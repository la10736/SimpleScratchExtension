__author__ = 'michele'

import unittest
from scratch.portability.mock import patch, Mock
from scratch.components import Sensor as S, SensorFactory as SF, Command as C, CommandFactory as CF, HatFactory as HF


class TestSensorFactory(unittest.TestCase):
    """Si tratta dei descrittori dei sensori. Definiscono il nome es la stringa di descrizione.
    Inoltre definiscono il valore di default che deve avere il sensore quando lo si costruisce.
    Devono avere il riferimento alla descrizione di estensione che li contiene.
    """

    def test_base(self):
        """Costructor take ExtensionDefinition as first argument and name as second"""
        med = Mock()
        self.assertRaises(TypeError, SF)
        self.assertRaises(TypeError, SF, med)
        sf = SF(med, 'test')
        self.assertIs(med, sf.ed)
        self.assertEqual('test', sf.name)
        self.assertEqual('test', sf.description)
        self.assertEqual('', sf.default)
        self.assertEqual('r', sf.type)

        """Check nominal arguments and the other parameters"""
        sf = SF(description='test test', default=1, ed=med, name='test')
        self.assertIs(med, sf.ed)
        self.assertEqual(('test', 'test test', 1), (sf.name, sf.description, sf.default))

        """ed can be None"""
        sf = SF(None, 'test', description='test test', default=1)
        self.assertIsNone(sf.ed)
        self.assertEqual(('test', 'test test', 1), (sf.name, sf.description, sf.default))


    def test_definition(self):
        """Give sensor definition as list to send as JSON object """
        sf = SF(ed=Mock(), name="goofy", default=1234, description="donald duck")
        self.assertListEqual(["r", "donald duck", "goofy"], sf.definition)

    def test_create(self):
        """Create the sensor object"""
        sf = SF(Mock(), 'test')
        mock_extension = Mock()
        self.assertRaises(TypeError, sf.create)
        s = sf.create(mock_extension, 1345)
        self.assertIsInstance(s, S)
        self.assertIs(s.extension, mock_extension)
        self.assertIs(s.info, sf)
        self.assertEqual(s.get(), 1345)

    def test_create_do_read(self):
        """Create a sensor object and set do_read() method"""
        sf = SF(Mock(), 'test')
        mock_extension = Mock()

        def do_read():
            return "goofy"

        s = sf.create(mock_extension, do_read=do_read)
        self.assertEqual(s.get(), "goofy")


class TestSensor(unittest.TestCase):
    """Sensor sono gli elementi base delle estensioni: internamente espongono la funzione di set()
    es come esetnsione quella di get() completamente sincrona. quando vengono costruite devono
    avere comunque un valore es rendono sempre un valore coerente"""

    def test_base(self):
        mock_e = Mock()  # Mock the extension
        mock_ed = Mock()  # Mock the extension definition

        """Costructor take extension as first argument and SensorFactory as second"""
        self.assertRaises(TypeError, S)
        self.assertRaises(TypeError, S, mock_e)
        sf = SF(mock_ed, "speed", default=10, description="The Speed")
        s = S(mock_e, sf)
        self.assertIs(s.extension, mock_e)
        self.assertIs(s.info, sf)
        self.assertEqual('speed', s.name)
        self.assertEqual('The Speed', s.description)
        self.assertEqual(10, s.get())
        self.assertEqual('r', s.type)

        """Check nominal argument and override value"""
        s = S(info=sf, value=13, extension=mock_e)
        self.assertIs(s.extension, mock_e)
        self.assertIs(s.info, sf)
        self.assertEqual(13, s.get())

    def test_proxy(self):
        """Check the proxy"""
        mock_e = Mock()  # Mock the extension
        mock_sf = Mock()  # Mock the sensor info
        s = S(mock_e, mock_sf)
        self.assertIs(s.type, mock_sf.type)
        self.assertIs(s.name, mock_sf.name)
        self.assertIs(s.description, mock_sf.description)
        self.assertIs(s.definition, mock_sf.definition)

    def test_get_and_set(self):
        mock_e = Mock()  # Mock the extension
        mock_sf = Mock()  # Mock the sensor info
        s = S(mock_e, mock_sf, value=56)
        self.assertEqual(56, s.get())
        s.set(67)
        self.assertEqual(67, s.get())
        s.set("hi")
        self.assertEqual("hi", s.get())

    @patch("threading.Lock")
    def test_get_and_set_syncronize(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock the extension
        mock_sf = Mock()  # Mock the sensor info
        s = S(mock_e, mock_sf, value=56)
        s.get()
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)
        m_lock.reset_mock()
        s.set("ss")
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)

    def test_reset(self):
        mock_e = Mock()  # Mock the extension
        mock_sf = Mock()  # Mock the sensor info
        s = S(mock_e, mock_sf)
        """just call s.reset()"""
        s.reset()
        s.reset(Mock())

    def test_do_read_behavior(self):
        mock_e = Mock()  # Mock the extension
        mock_sf = Mock()  # Mock the sensor info
        s = S(mock_e, mock_sf)
        s.set("ss")
        self.assertEqual("ss", s.get())
        s.do_read = lambda: "AA"
        self.assertEqual("AA", s.get())

    def test_get_cgi(self):
        mock_e = Mock()  # Mock the extension
        mock_sf = Mock()  # Mock the sensor info
        s = S(mock_e, mock_sf)
        self.assertIsNone(s.get_cgi("a"))

    def test_create(self):
        mock_e = Mock()
        s = S.create(mock_e, "sensor")
        self.assertIs(mock_e, s.extension)
        self.assertEqual(s.name, "sensor")

        def do_read():
            return "goofy"

        s = S.create(mock_e, "sensor2", default="S", description="ASD", do_read=do_read)
        self.assertIs(mock_e, s.extension)
        self.assertEqual(s.name, "sensor2")
        self.assertEqual(s.info.default, "S")
        self.assertEqual(s.description, "ASD")
        self.assertEqual(s.get(), "goofy")


class TestCommandFactory(unittest.TestCase):
    """We are testing the commands descriptors. They define name and description."""

    @patch("scratch.components.CommandFactory._check_description", return_value=True)
    def test_base(self, mock_check_description):
        """Costructor take ExtensionDefinition as first argument and name as second"""
        med = Mock()
        self.assertRaises(TypeError, CF)
        self.assertRaises(TypeError, CF, med)
        cf = CF(med, 'test')
        self.assertIs(med, cf.ed)
        self.assertEqual('test', cf.name)
        self.assertEqual('test', cf.description)
        self.assertEqual((), cf.default)
        self.assertEqual(' ', cf.type)
        self.assertDictEqual({}, cf.menu_dict)

        """Check nominal arguments and the other parameters"""
        cf = CF(description=r'test %n test %s nnn %b', default=(1, "goofy"), ed=med, name='test',
                men1=[1, 2, 3], men2=["a", "b", "c"])
        self.assertIs(med, cf.ed)
        self.assertEqual(('test', r'test %n test %s nnn %b', (1, "goofy"),
                          {"men1": [1, 2, 3], "men2": ["a", "b", "c"]}),
                         (cf.name, cf.description, cf.default, cf.menu_dict))

        """ed can be None"""
        cf = CF(None, 'test', description=r'test %n test %s nnn %b')
        self.assertIsNone(cf.ed)
        self.assertEqual(('test', r'test %n test %s nnn %b'), (cf.name, cf.description))

        mock_check_description.return_value = False
        self.assertRaises(ValueError, CF, med, 'test')


    def test_parse_description(self):
        """"return a list of callable functions to convert arguments or names (string) of menu"""
        self.fail("IMPLEMENT")

    def test__check_description(self):
        self.fail("IMPLEMENT")

    @patch("scratch.components.CommandFactory._check_description", return_value=True)
    def test_definition(self, mock_check_description):
        """Give command definition as list to send as JSON object """
        cf = CF(ed=Mock(), name="goofy", default=(1234, "a"), description="donald duck")
        self.assertListEqual([" ", "donald duck", "goofy", 1234, "a"], cf.definition)
        cf = CF(ed=Mock(), name="sss")
        self.assertListEqual([" ", "sss", "sss"], cf.definition)

    def test_create(self):
        """Create the command object"""
        cf = CF(Mock(), 'test')
        mock_extension = Mock()
        self.assertRaises(TypeError, cf.create)
        c = cf.create(mock_extension)
        self.assertIsInstance(c, C)
        self.assertIs(c.extension, mock_extension)
        self.assertIs(c.info, cf)

    def test_create_do_command(self):
        """Create a command object and set do_command(*args) method"""
        cf = CF(Mock(), 'test')
        mock_extension = Mock()
        v = []

        def do_command(*args):
            v.append(args)

        c = cf.create(mock_extension, do_command=do_command)
        c.command("minnie", "goofy")
        self.assertEqual(v[-1], ("minnie", "goofy"))


class TestCommand(unittest.TestCase):
    """Command components perform actions and return. User application should override
    the method do_command(*args) to do the real work.
    the property value return last value (None if no call or tuple if it haa more argument)
    """

    def test_base(self):
        mock_e = Mock()  # Mock the extension
        mock_ed = Mock()  # Mock the extension definition

        """Costructor take extension as first argument and SensorFactory as second"""
        self.assertRaises(TypeError, C)
        self.assertRaises(TypeError, C, mock_e)

        cf = CF(ed=mock_ed, name="beep", description="Say BEEP")
        c = C(mock_e, cf)
        self.assertIs(c.extension, mock_e)
        self.assertIs(c.info, cf)
        self.assertIsNone(c.value)
        self.assertEqual('beep', c.name)
        self.assertEqual('Say BEEP', c.description)
        self.assertEqual(' ', c.type)

        """Check nominal argument and override value"""
        c = C(info=cf, extension=mock_e)
        self.assertIs(c.extension, mock_e)
        self.assertIs(c.info, cf)

    def test_proxy(self):
        """Check the proxy"""
        mock_e = Mock()  # Mock the extension
        mock_cf = Mock()  # Mock the command info
        c = C(mock_e, mock_cf)
        self.assertIs(c.type, mock_cf.type)
        self.assertIs(c.name, mock_cf.name)
        self.assertIs(c.description, mock_cf.description)
        self.assertIs(c.definition, mock_cf.definition)

    def test_command(self):
        mock_e = Mock()  # Mock the extension
        mock_cf = Mock()  # Mock the command info
        c = C(mock_e, mock_cf)
        self.assertIsNone(c.value)
        c.command("agr1", "agr2", "agr3")
        self.assertEqual(("agr1", "agr2", "agr3"), c.value)
        c.command("argument")
        self.assertEqual("argument", c.value)
        c.command()
        self.assertEqual((), c.value)

        v = []

        def cmd(a, b):
            v.append(a)
            v.append(b)

        c.do_command = cmd
        c.command("A", "B")
        self.assertEqual(v, ["A", "B"])
        self.assertEqual(("A", "B"), c.value)

    def test_do_command_check_arguments(self):
        mock_e = Mock()  # Mock the extension
        mock_cf = Mock()  # Mock the command info
        c = C(mock_e, mock_cf)
        c.do_command = lambda: None
        c.command()
        self.assertRaises(TypeError, c.command, "a")

    @patch("threading.Lock")
    def test_command_and_value_syncronize(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock the extension
        mock_cf = Mock()  # Mock the sensor info
        c = C(mock_e, mock_cf)
        c.command()
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)
        m_lock.reset_mock()
        _ = c.value
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)

    def test_reset(self):
        mock_e = Mock()  # Mock the extension
        mock_cf = Mock()  # Mock the sensor info
        c = C(mock_e, mock_cf)
        """just call c.reset()"""
        c.reset()
        c.reset(Mock())

    def test_get_cgi(self):
        mock_e = Mock()  # Mock the extension
        mock_cf = Mock()  # Mock the sensor info
        mock_cf.name = "My Name"
        c = C(mock_e, mock_cf)
        self.assertIsNone(c.get_cgi("not your cgi"))
        self.assertIsNone(c.get_cgi("My%20Name"))
        """Must start by /"""
        cgi = c.get_cgi("/My%20Name")
        self.assertIsNotNone(cgi)
        self.assertEqual({}, cgi.headers)
        with patch.object(c, "command", autospec=True) as mock_command:
            self.assertEqual("", cgi(Mock(path="My%20Name")))
            mock_command.assert_called_with()
            mock_command.reset_mock
            self.assertEqual("", cgi(Mock(path="My%20Name/a/b/c%20d/1234")))
            mock_command.assert_called_with("a", "b", "c d", "1234")

    def test_create(self):
        mock_e = Mock()
        c = C.create(mock_e, "control")
        self.assertIs(mock_e, c.extension)
        self.assertEqual(c.name, "control")

        v = []

        def do_command(*args):
            v.append(args)

        c = C.create(mock_e, "control2", (1, 2, 3), description="ASD", do_command=do_command)
        self.assertIs(mock_e, c.extension)
        self.assertEqual(c.name, "control2")
        self.assertEqual(c.info.default, (1, 2, 3))
        self.assertEqual(c.description, "ASD")
        c.command("a","b")
        self.assertEqual(v[-1],("a","b"))


class TestHatFactory(unittest.TestCase):
    """We are testing the hat descriptors. They define name and description."""

    def test_base(self):
        """Costructor take ExtensionDefinition as first argument and name as second"""
        med = Mock()
        self.assertRaises(TypeError, HF)
        self.assertRaises(TypeError, HF, med)
        hf = HF(med, 'test')
        self.assertIs(med, hf.ed)
        self.assertEqual('test', hf.name)
        self.assertEqual('test', hf.description)
        self.assertEqual('h', hf.type)
        self.assertDictEqual({}, hf.menu_dict)

        """Check nominal arguments and the other parameters"""
        hf = HF(description=r'test %n test %s nnn %b', ed=med, name='test',
                men1=[1, 2, 3], men2=["a", "b", "c"])
        self.assertIs(med, hf.ed)
        self.assertEqual(('test', r'test %n test %s nnn %b',
                          {"men1": [1, 2, 3], "men2": ["a", "b", "c"]}),
                         (hf.name, hf.description, hf.menu_dict))

        """ed can be None"""
        hf = HF(None, 'test', description=r'test %n test %s nnn %b')
        self.assertIsNone(hf.ed)
        self.assertEqual(('test', r'test %n test %s nnn %b'), (hf.name, hf.description))


    # def test_parse_description(self):
    #     """"return a list of callable functions to convert arguments or names (string) of menu"""
    #     self.fail("IMPLEMENT")
    #
    # def test__check_description(self):
    #     self.fail("IMPLEMENT")
    #
    # @patch("scratch.components.CommandFactory._check_description", return_value=True)
    # def test_definition(self, mock_check_description):
    #     """Give command definition as list to send as JSON object """
    #     cf = CF(ed=Mock(), name="goofy", default=(1234, "a"), description="donald duck")
    #     self.assertListEqual([" ", "donald duck", "goofy", 1234, "a"], cf.definition)
    #     cf = CF(ed=Mock(), name="sss")
    #     self.assertListEqual([" ", "sss", "sss"], cf.definition)
    #
    # def test_create(self):
    #     """Create the command object"""
    #     cf = CF(Mock(), 'test')
    #     mock_extension = Mock()
    #     self.assertRaises(TypeError, cf.create)
    #     c = cf.create(mock_extension)
    #     self.assertIsInstance(c, C)
    #     self.assertIs(c.extension, mock_extension)
    #     self.assertIs(c.info, cf)
    #
    # def test_create_do_command(self):
    #     """Create a command object and set do_command(*args) method"""
    #     cf = CF(Mock(), 'test')
    #     mock_extension = Mock()
    #     v = []
    #
    #     def do_command(*args):
    #         v.append(args)
    #
    #     c = cf.create(mock_extension, do_command=do_command)
    #     c.command("minnie", "goofy")
    #     self.assertEqual(v[-1], ("minnie", "goofy"))



if __name__ == '__main__':
    unittest.main()
