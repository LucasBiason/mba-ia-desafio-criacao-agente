"""Regressão de entrada inválida e preservação das credenciais."""
import unittest
from pydantic import ValidationError
from services.authentication.schemas.login import Login
from services.users.schemas.account_create import AccountCreate
from services.users.schemas.account_patch import AccountPatch


class IdentityInputTest(unittest.TestCase):
    def test_null_bytes_rejected_before_persistence(self):
        valid = {'name': 'Pessoa de teste', 'email': 'person@aurora.test', 'password': ' Secret-Test-Password '}
        for schema, base, fields in (
            (AccountCreate, valid, ('name', 'email', 'password')),
            (AccountPatch, {}, ('name', 'email', 'password')),
            (Login, {'email': valid['email'], 'password': valid['password']}, ('email', 'password')),
        ):
            for field in fields:
                with self.subTest(schema=schema.__name__, field=field):
                    value = 'nul\x00@aurora.test' if field == 'email' else 'Invalid\x00TestPassword'
                    with self.assertRaises(ValidationError):
                        schema(**{**base, field: value})

    def test_password_spaces_are_preserved(self):
        password = ' Secret-Test-Password '
        for value in (
            Login(email=' PERSON@AURORA.TEST ', password=password),
            AccountCreate(name=' Person ', email=' PERSON@AURORA.TEST ', password=password),
            AccountPatch(password=password),
        ):
            self.assertEqual(value.password, password)
        self.assertEqual(Login(email=' PERSON@AURORA.TEST ', password=password).email, 'person@aurora.test')
        self.assertEqual(AccountCreate(name=' Person ', email='person@aurora.test', password=password).name, 'Person')


if __name__ == '__main__':
    unittest.main()
