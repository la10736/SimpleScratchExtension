from unittest.mock import patch, Mock

__author__ = 'michele'

import unittest
from scratch.extension import Extension as E


class TestExtension(unittest.TestCase):
    """Contenitore che presenta sia internamente che esternamente i componenti:
    - Ha i singoli oggetti
    - Risponde alle richieste del web server
    """

    def test_base(self):
        e = E("pippo")
        self.assertIsNotNone(e)
        self.assertEqual("pippo", e.name)
        self.assertRaises(TypeError, E)

    @patch("scratch.extension.Extension._register_components")
    @patch("scratch.components.Sensor")
    def test_sensor_extension_factory(self, m, mrc):
        """Verifica le funzioni della factory"""
        e = E("e")
        e.create_sensor("aa")
        m.assert_called_with(e, value="aa")
        mrc.assert_called_with(component=m.return_value)

    def test_components(self):
        """Rende l'insieme NON modificabile dei coponenti"""
        e = E("e")
        components = e.components
        self.assertSetEqual(set(), components)
        self.assertFalse(hasattr(components, "add"))

    def test__register_components(self):
        """Verificare che il componente venga registrato nell'insimeme dei componenti usando
        la property."""
        e = E("e")
        c = Mock()
        e._register_components(c)
        self.assertIn(c, e.components)
        self.assertEqual(1, len(e.components))
        """Doppio ignorato"""
        e._register_components(c)
        self.assertIn(c, e.components)
        self.assertEqual(1, len(e.components))
        d = Mock()
        e._register_components(d)
        self.assertSetEqual({c, d}, e.components)
        """Register components prende anche piu' di un elemento"""
        f, g, h, i = (Mock() for _ in range(4))
        e._register_components(f, g, h, i)
        self.assertSetEqual({c, d, f, g, h, i}, e.components)

        """Due components con lo stesso name non possono essere registrati"""
        self.fail("""Due components con lo stesso name non possono essere registrati""")

    def test__deregister_component(self):
        """Verificare che il componente venga deregistrato dall'insimeme dei componenti usando
        la property."""
        e = E("e")
        components = [Mock() for _ in range(4)]
        e._register_components(*components)
        for c in components:
            e._deregister_components(c)
            self.assertNotIn(c, e.components)
        self.assertSetEqual(set(), e.components)
        components = [Mock() for _ in range(4)]
        e._register_components(*components)
        e._deregister_components(*components)
        self.assertSetEqual(set(), e.components)
        self.assertRaises(KeyError, e._deregister_components, Mock())



if __name__ == '__main__':
    unittest.main()
