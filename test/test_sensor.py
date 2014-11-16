from unittest.mock import patch, Mock

__author__ = 'michele'

import unittest
from scratch.components import Sensor as S
from scratch.extension import Extension as E


class TestSensor(unittest.TestCase):
    """Sensor sono gli elementi base delle estensioni: internamente espongono la funzione di set()
    e come esetnsione quella di get() completamente sincrona. quando vengono costruite devono
    avere comunque un valore e rendono sempre un valore coerente"""

    @patch("scratch.extension.Extension")
    def test_base(self, m):
        """La costruzione prende sempre una extension come primo argomento"""
        self.assertRaises(TypeError, S)
        s = S(m.return_value, name="prova")
        self.assertIs(s.extension, m.return_value)
        self.assertEqual('prova', s.name)
        self.assertEqual('prova', s.description)
        self.assertEqual('', s.get())
        self.assertEqual('r', s.type)

        """Description e value possono cambiare"""
        s = S(m.return_value, name="pippo", value=1234, description="paperino")
        self.assertEqual('pippo', s.name)
        self.assertEqual('paperino', s.description)
        self.assertEqual(1234, s.get())
        self.assertEqual('r', s.type)

    def test_definition(self):
        """Rende i dati del componente come lista che viene inserita nell'oggeto JSON che descrive l'estensione"""
        s = S(Mock(), name="pippo", value=1234, description="paperino")
        self.assertListEqual(["r", "paperino", "pippo"], s.definition)


if __name__ == '__main__':
    unittest.main()
