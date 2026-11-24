"""Catalog aliases must resolve deterministically without guessing another area."""

import unittest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine
from sqlalchemy.orm import Session
from services.common_areas.models.area import Area
from services.agent.repositories.product_action_repository import (
    ProductActionRepository,
)


class AreaCatalogResolutionTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        # Test catalog resolution with the real ORM on a portable table;
        # PostgreSQL-specific CHECK constraints belong to PostgreSQL E2E.
        Table(
            "areas",
            MetaData(),
            Column("id", String, primary_key=True),
            Column("name", String, nullable=False),
            Column("fee_cents", Integer, nullable=False),
        ).create(self.engine)
        self.session = Session(self.engine)
        self.session.add_all(
            [
                Area(id="salao-de-festas", name="Salão de festas", fee_cents=15000),
                Area(id="quadra", name="Quadra poliesportiva", fee_cents=0),
                Area(id="espaco-livre", name="Espaço Livre", fee_cents=0),
            ]
        )
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_common_abbreviation_matches_only_catalog_area(self):
        for value in ("salão", "SALAO", "salão de festas", "salao-de-festas"):
            with self.subTest(value=value):
                self.assertEqual(
                    ProductActionRepository._area(self.session, value).id,
                    "salao-de-festas",
                )

    def test_ambiguous_prefix_is_never_arbitrarily_selected(self):
        self.session.add(Area(id="salao-de-jogos", name="Salão de jogos", fee_cents=0))
        self.session.commit()
        self.assertIsNone(ProductActionRepository._area(self.session, "salão"))
        self.assertEqual(
            ProductActionRepository._area(self.session, "salão de festas").id,
            "salao-de-festas",
        )

    def test_partial_word_and_unknown_name_do_not_match(self):
        for value in ("sal", "cinema", "festas", "", None):
            self.assertIsNone(ProductActionRepository._area(self.session, value))

    def test_exact_name_and_id_keep_existing_behavior(self):
        for value in ("quadra", "Quadra poliesportiva", "Espaço Livre"):
            self.assertIsNotNone(ProductActionRepository._area(self.session, value))

    def test_missing_area_is_not_invented(self):
        self.assertIsNone(ProductActionRepository._area(self.session, "piscina"))
