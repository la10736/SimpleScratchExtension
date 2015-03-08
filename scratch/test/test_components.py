import copy
import threading

from mock import ANY, call, MagicMock


__author__ = 'michele'

import unittest
from scratch.portability.mock import patch, Mock
from scratch.components import Sensor as S, SensorFactory as SF, \
    Command as C, CommandFactory as CF, HatFactory as HF, Hat as H, \
    WaiterCommand as W, WaiterCommandFactory as WF, Requester as R, \
    RequesterFactory as RF, BooleanBlock as B, BooleanFactory as BF, \
    Reporter as RR, ReporterFactory as RRF
from scratch.components import parse_description, to_bool


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

    def test_is_a_ReporterFactory_instance(self):
        sf = SF(Mock(), 'test')
        self.assertIsInstance(sf, RRF)

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
        self.assertEqual(10, s.value)
        self.assertEqual('r', s.type)

        """Check nominal argument and override value"""
        s = S(info=sf, value=13, extension=mock_e)
        self.assertIs(s.extension, mock_e)
        self.assertIs(s.info, sf)
        self.assertEqual(13, s.value)

    def test_proxy(self):
        """Check the proxy"""
        mock_e = Mock()  # Mock the extension
        mock_sf = MagicMock()  # Mock the sensor info
        s = S(mock_e, mock_sf)
        self.assertIs(s.type, mock_sf.type)
        self.assertIs(s.name, mock_sf.name)
        self.assertIs(s.description, mock_sf.description)
        self.assertIs(s.definition, mock_sf.definition)

    def test_get_and_set(self):
        mock_e = Mock()  # Mock the extension
        mock_sf = MagicMock()  # Mock the sensor info
        s = S(mock_e, mock_sf, value=56)
        self.assertEqual(56, s.get())
        s.set(67)
        self.assertEqual(67, s.get())
        s.set("hi")
        self.assertEqual("hi", s.get())

    @patch("threading.RLock")
    def test_get_and_set_synchronize(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock the extension
        mock_sf = MagicMock()  # Mock the sensor info
        s = S(mock_e, mock_sf, value=56)
        s.get()
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)
        m_lock.reset_mock()
        s.set("ss")
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)

    def test_value(self):
        """1) return last computed value
           2) synchronize
        """
        mock_e = Mock()  # Mock the extension
        mock_sf = MagicMock()  # Mock the sensor info
        v = 0

        def get():
            return v

        s = S(mock_e, mock_sf, value=56)
        s.do_read = get

        self.assertEqual(56, s.value)
        s.get()
        self.assertEqual(0, s.value)
        v = 12
        self.assertEqual(0, s.value)
        s.get()
        self.assertEqual(12, s.value)
        s.set(32)
        self.assertEqual(32, s.value)
        self.assertEqual(32, s.value)
        s.get()
        self.assertEqual(12, s.value)

        with patch("threading.RLock") as m_lock:
            m_lock = m_lock.return_value
            """We must rebuild s to mock lock"""
            s = S(mock_e, mock_sf, value=56)
            s.value
            self.assertTrue(m_lock.__enter__.called)
            self.assertTrue(m_lock.__exit__.called)
            m_lock.reset_mock()
            s._set_value(32)
            self.assertTrue(m_lock.__enter__.called)
            self.assertTrue(m_lock.__exit__.called)

    def test_reset(self):
        mock_e = Mock()  # Mock the extension
        mock_sf = MagicMock()  # Mock the sensor info
        s = S(mock_e, mock_sf)
        """just call s.reset()"""
        s.reset()

    @patch("threading.RLock")
    def test_reset_synchronize(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock the extension
        mock_sf = MagicMock()  # Mock the sensor info
        s = S(mock_e, mock_sf)
        """just call s.reset()"""
        s.reset()
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)


    def test_do_read_behavior(self):
        mock_e = Mock()  # Mock the extension
        mock_sf = MagicMock()  # Mock the sensor info
        s = S(mock_e, mock_sf)
        s.set("ss")
        self.assertEqual("ss", s.get())
        s.do_read = lambda: "AA"
        self.assertEqual("AA", s.get())

    def test_get_cgi(self):
        mock_e = Mock()  # Mock the extension
        mock_sf = MagicMock()  # Mock the sensor info
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

    def test_poll(self):
        v = 41

        def r():
            return v

        mock_e = Mock()
        s = S.create(mock_e, "sensor", do_read=r)
        self.assertDictEqual({(): v}, s.poll())
        v = 13
        self.assertDictEqual({(): v}, s.poll())


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


    @unittest.skip("Not Implementetd yet")
    def test_parse_description(self):
        """"return a list of callable functions to convert arguments or names (string) of menu"""
        self.fail("IMPLEMENT")

    @unittest.skip("Not Implementetd yet")
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

        """Costructor take extension as first argument and CommandFactory as second"""
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
        mock_cf = MagicMock()  # Mock the command info
        c = C(mock_e, mock_cf)
        self.assertIs(c.type, mock_cf.type)
        self.assertIs(c.name, mock_cf.name)
        self.assertIs(c.description, mock_cf.description)
        self.assertIs(c.definition, mock_cf.definition)

    def test_command(self):
        mock_e = Mock()  # Mock the extension
        cf = CF(mock_e, 'test', description="Execute")
        c = C(mock_e, cf)
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
        cf = CF(mock_e, 'test', description="Execute")
        c = C(mock_e, cf)
        c.do_command = lambda: None
        c.command()
        self.assertRaises(TypeError, c.command, "a")

    @patch("threading.RLock")
    def test_command_and_value_synchronize(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock the extension
        cf = CF(mock_e, 'test', description="Execute")
        c = C(mock_e, cf)
        c.command()
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)
        m_lock.reset_mock()
        _ = c.value
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)

    def test_reset(self):
        mock_e = Mock()  # Mock the extension
        mock_cf = MagicMock()  # Mock the sensor info
        c = C(mock_e, mock_cf)
        """just call c.reset()"""
        c.reset()

    @patch("threading.RLock")
    def test_reset_synchronize(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock the extension
        mock_cf = MagicMock()  # Mock the command info
        c = C(mock_e, mock_cf)
        """just call c.reset()"""
        c.reset()
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)

    def test_get_cgi(self):
        mock_e = Mock()  # Mock the extension
        mock_cf = Mock()  # Mock the sensor info
        mock_cf.name = "My Name"
        cf = CF(mock_e, name='My Name', description="Execute")
        c = C(mock_e, cf)
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
        c.command("a", "b")
        self.assertEqual(v[-1], ("a", "b"))

    def test_poll(self):
        mock_e = Mock()
        c = C.create(mock_e, "command")
        self.assertDictEqual({}, c.poll())


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


    def test_definition(self):
        """Give command definition as list to send as JSON object """
        hf = HF(ed=Mock(), name="goofy", description="donald duck")
        self.assertListEqual(["h", "donald duck", "goofy"], hf.definition)
        hf = HF(ed=Mock(), name="sss")
        self.assertListEqual(["h", "sss", "sss"], hf.definition)

    def test_create(self):
        """Create the hat object"""
        hf = HF(Mock(), 'test')
        mock_extension = Mock()
        self.assertRaises(TypeError, hf.create)
        h = hf.create(mock_extension)
        self.assertIsInstance(h, H)
        self.assertIs(h.extension, mock_extension)
        self.assertIs(h.info, hf)

    def test_create_do_flag(self):
        """Create a hat object and set do_flag() method (a callback that give True
        when you want raise the event
        """
        hf = HF(Mock(), 'test')
        mock_extension = Mock()
        flag = False

        def do_flag(*args):
            return flag

        h = hf.create(mock_extension, do_flag=do_flag)
        self.assertEqual(False, h.state)
        flag = True
        self.assertEqual(True, h.state)
        flag = "a"
        self.assertEqual(True, h.state)
        flag = ""
        self.assertEqual(False, h.state)


class TestHat(unittest.TestCase):
    """Hat blocks return True to raise a event. User application should call flag() to
    raise event or override do_flag() method that return True when want to raise event.
    """

    def test_base(self):
        mock_e = Mock()  # Mock the extension
        mock_ed = Mock()  # Mock the extension definition

        """Costructor take extension as first argument and SensorFactory as second"""
        self.assertRaises(TypeError, H)
        self.assertRaises(TypeError, H, mock_e)

        hf = HF(ed=mock_ed, name="alarm", description="Do alarm")
        h = H(mock_e, hf)
        self.assertIs(h.extension, mock_e)
        self.assertIs(h.info, hf)
        self.assertFalse(h.state)
        self.assertEqual('alarm', h.name)
        self.assertEqual('Do alarm', h.description)
        self.assertEqual('h', h.type)

        """Check nominal argument and override value"""
        h = H(info=hf, extension=mock_e)
        self.assertIs(h.extension, mock_e)
        self.assertIs(h.info, hf)

    def test_proxy(self):
        """Check the proxy"""
        mock_e = Mock()  # Mock the extension
        mock_hf = MagicMock()  # Mock the command info
        h = H(mock_e, mock_hf)
        self.assertIs(h.type, mock_hf.type)
        self.assertIs(h.name, mock_hf.name)
        self.assertIs(h.description, mock_hf.description)
        self.assertIs(h.definition, mock_hf.definition)

    def test_flag(self):
        mock_e = Mock()  # Mock the extension
        mock_hf = MagicMock()  # Mock the boolean info
        h = H(mock_e, mock_hf)
        self.assertFalse(h.state)
        h.flag()
        self.assertTrue(h.state)
        self.assertFalse(h.state)
        h.flag()
        self.assertTrue(h.state)
        self.assertFalse(h.state)

        v = False

        def flag():
            return v

        h.do_flag = flag
        self.assertFalse(h.state)
        v = True
        self.assertTrue(h.state)
        self.assertTrue(h.state)
        v = False
        self.assertFalse(h.state)
        h.flag()
        self.assertFalse(h.state)

        del h.do_flag
        self.assertTrue(h.state)
        self.assertFalse(h.state)
        h.flag()
        self.assertTrue(h.state)
        self.assertFalse(h.state)

    @patch("threading.RLock")
    def test_flag_and_state_synchronize_do_flag_no(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock the extension
        mock_hf = MagicMock()  # Mock the hat info
        h = H(mock_e, mock_hf)
        h.flag()
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)
        m_lock.reset_mock()
        _ = h.state
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)
        m_lock.reset_mock()
        h.do_flag = lambda: _
        _ = h.state
        self.assertFalse(m_lock.__enter__.called)
        self.assertFalse(m_lock.__exit__.called)

    def test_reset(self):
        mock_e = Mock()  # Mock the extension
        mock_hf = MagicMock()  # Mock the hat info
        h = H(mock_e, mock_hf)
        """call h.reset() and check i f flag reset"""
        h.flag()
        h.reset()
        self.assertFalse(h.state)

    @patch("threading.RLock")
    def test_reset_synchronize(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock the extension
        mock_hf = MagicMock()  # Mock the hat info
        h = H(mock_e, mock_hf)
        h.reset()
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)

    def test_get_cgi(self):
        mock_e = Mock()  # Mock the extension
        mock_hf = MagicMock()  # Mock the hat info
        h = H(mock_e, mock_hf)
        self.assertIsNone(h.get_cgi("a"))

    def test_create(self):
        mock_e = Mock()
        h = H.create(mock_e, "hat")
        self.assertIs(mock_e, h.extension)
        self.assertEqual(h.name, "hat")

        v = "goofy"

        def do_flag():
            return v

        h = H.create(mock_e, "hat2", description="ASD", do_flag=do_flag)
        self.assertIs(mock_e, h.extension)
        self.assertEqual(h.name, "hat2")
        self.assertEqual(h.description, "ASD")
        self.assertEqual(h.state, True)
        v = ""
        self.assertEqual(h.state, False)
        v = None
        self.assertEqual(h.state, False)
        v = True
        self.assertEqual(h.state, True)

    def test_poll(self):
        mock_e = Mock()
        h = H.create(mock_e, "hat")
        self.assertDictEqual({}, h.poll())


class TestWaiterCommandFactory(unittest.TestCase):
    """We are testing the commands that can wait descriptors. They define name and description."""

    @patch("scratch.components.WaiterCommandFactory._check_description", return_value=True)
    def test_base(self, mock_check_description):
        """Costructor take ExtensionDefinition as first argument and name as second"""
        med = Mock()
        self.assertRaises(TypeError, WF)
        self.assertRaises(TypeError, WF, med)
        wf = WF(med, 'test')
        self.assertIs(med, wf.ed)
        self.assertEqual('test', wf.name)
        self.assertEqual('test', wf.description)
        self.assertEqual((), wf.default)
        self.assertEqual('w', wf.type)
        self.assertDictEqual({}, wf.menu_dict)

    def test_is_a_CommandFactory_instance(self):
        wf = WF(Mock(), 'test')
        self.assertIsInstance(wf, CF)

    def test_create(self):
        """Create the waiter command object"""
        wf = WF(Mock(), 'test')
        mock_extension = Mock()
        self.assertRaises(TypeError, wf.create)
        w = wf.create(mock_extension)
        self.assertIsInstance(w, W)
        self.assertIs(w.extension, mock_extension)
        self.assertIs(w.info, wf)


class TestWaiterCommand(unittest.TestCase):
    """Waiter command components perform asynchronous command. User application should override
    the method do_command(*args) to do the real work, the library will run in a new thread and
    take care of put it in busy state until ends. For general behaviour look Command
    """

    def test_base(self):
        mock_e = Mock()  # Mock the extension
        mock_ed = Mock()  # Mock the extension definition

        """Costructor take extension as first argument and WaiterCommandFactory as second"""
        self.assertRaises(TypeError, W)
        self.assertRaises(TypeError, W, mock_e)

        wf = WF(ed=mock_ed, name="beep", description="Say BEEP and wait")
        w = W(mock_e, wf)
        self.assertIs(w.extension, mock_e)
        self.assertIs(w.info, wf)
        self.assertIsNone(w.value)
        self.assertEqual('beep', w.name)
        self.assertEqual('Say BEEP and wait', w.description)
        self.assertEqual('w', w.type)

    def test_is_Command_subclass(self):
        mock_e = Mock()  # Mock the extension
        mock_cf = MagicMock()  # Mock the command info
        w = W(mock_e, mock_cf)
        self.assertIsInstance(w, C)

    def test_execute_busy_command(self):
        """Remove the busy argument even if there is an exception
        """
        mock_e = Mock()  # Mock the extension
        mock_cf = MagicMock()  # Mock the command info
        w = W(mock_e, mock_cf)
        busy = 12345
        self.assertFalse(w.busy)
        w._busy.add(busy)

        def do_command(a, b):
            self.assertIn(busy, w.busy)
            self.assertEqual(a, "a")
            self.assertEqual(b, "b")

        w.do_command = do_command
        w.execute_busy_command(busy, "a", "b")
        self.assertFalse(w.busy)

        """Work even busy is not in bust set"""

        def do_command(a, b):
            pass

        w.do_command = do_command
        w.execute_busy_command(busy, "a", "b")
        self.assertFalse(w.busy)

        w._busy.add(busy)

        def do_command(a, b):
            self.assertIn(busy, w.busy)
            raise Exception()

        w.do_command = do_command
        self.assertRaises(Exception, w.execute_busy_command, busy, "a", "b")
        self.assertFalse(w.busy)

    def test_command_start_thread_to_execute_execute_busy_command(self):
        """Add busy, create thread with execute_busy_command target, set daemon to True and start thread.

        Only if extension implement do_command()
        """
        mock_e = Mock()  # Mock the extension
        mock_cf = MagicMock()  # Mock the command info
        w = W(mock_e, mock_cf)
        busy = 12345
        w.do_command = Mock()
        with patch("threading.Thread", autospec=True) as mock_thread_class:
            mock_thread = mock_thread_class.return_value
            w.command(busy, "a")
            self.assertIn(busy, w._busy)
            mock_thread_class.assert_called_with(name=ANY, target=w.execute_busy_command, args=(busy, "a"))
            mock_thread.setDaemon.assert_called_with(True)
            self.assertTrue(mock_thread.start.called)
        """Sanity chack without mocks"""
        w.command(busy, "a")

        """Without do_command"""
        del w.do_command
        with patch("threading.Thread", autospec=True) as mock_thread_class:
            w.command(busy, "a")
            self.assertFalse(mock_thread_class.called)
        """Sanity chack without mocks"""
        w.command(busy, "a")

    @patch("threading.RLock")
    def test_busy_access_synchronize(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock the extension
        mock_cf = MagicMock()  # Mock the sensor info
        w = W(mock_e, mock_cf)
        w.busy
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)
        m_lock.reset_mock()

        def do_command():
            # Check busy add
            self.assertTrue(m_lock.__enter__.called)
            self.assertTrue(m_lock.__exit__.called)
            m_lock.reset_mock()

        w.do_command = do_command
        w.command(1234)

        def do_command():
            pass

        w.do_command = do_command
        m_lock.reset_mock()
        w.execute_busy_command(1234)
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)

    def test_reset(self):
        """Should reset busy set"""
        mock_e = Mock()  # Mock the extension
        mock_cf = MagicMock()  # Mock the sensor info
        w = W(mock_e, mock_cf)
        w._busy_add(1234)
        w._busy_add(2234)
        w._busy_add(3234)
        self.assertSetEqual(w.busy, {1234, 2234, 3234})
        w.reset()
        self.assertSetEqual(w.busy, set())

        with patch("threading.RLock") as m_lock:
            m_lock = m_lock.return_value
            """Must rebuild to hane the mock"""
            w = W(mock_e, mock_cf)
            w.reset()
            self.assertTrue(m_lock.__enter__.called)
            self.assertTrue(m_lock.__exit__.called)

    def test_get_cgi(self):
        mock_e = Mock()  # Mock the extension
        mock_wf = MagicMock()  # Mock the waiter command info
        mock_wf.name = "My Name"
        w = W(mock_e, mock_wf)
        self.assertIsNone(w.get_cgi("not your cgi"))
        self.assertIsNone(w.get_cgi("My%20Name"))
        """Must start by / and contain at least one argument : busy"""
        self.assertIsNone(w.get_cgi("/My%20Name"))
        """The first must be integer"""
        self.assertIsNone(w.get_cgi("/My%20Name/mybusy"))
        cgi = w.get_cgi("/My%20Name/1234")
        self.assertIsNotNone(cgi)
        self.assertEqual({}, cgi.headers)
        with patch.object(w, "command", autospec=True) as mock_command:
            self.assertEqual("", cgi(Mock(path="My%20Name/3452")))
            mock_command.assert_called_with(3452)
            mock_command.reset_mock
            self.assertEqual("", cgi(Mock(path="My%20Name/54321/b/c%20d/1234")))
            mock_command.assert_called_with(54321, "b", "c d", "1234")

    def test_create(self):
        mock_e = Mock()
        w = W.create(mock_e, "control")
        self.assertIsInstance(w, W)
        self.assertIs(mock_e, w.extension)
        self.assertEqual(w.name, "control")
        self.assertEqual(w.type, "w")

        v = []

        def do_command(*args):
            v.append(args)

        w = W.create(mock_e, "control2", (1, 2, 3), description="ASD", do_command=do_command)
        self.assertIsInstance(w, W)
        self.assertIs(mock_e, w.extension)
        self.assertEqual(w.name, "control2")
        self.assertEqual(w.info.default, (1, 2, 3))
        self.assertEqual(w.description, "ASD")
        self.assertIs(do_command, w.do_command)

    def test_poll(self):
        mock_e = Mock()
        w = W.create(mock_e, "wcommand")
        self.assertDictEqual({}, w.poll())


class TestRequesterFactory(unittest.TestCase):
    """We are testing requester descriptors (reporters that can wait). They define name and description."""

    def test_base(self):
        """Costructor take ExtensionDefinition as first argument and name as second"""
        med = Mock()
        self.assertRaises(TypeError, RF)
        self.assertRaises(TypeError, RF, med)
        rf = RF(med, 'test')
        self.assertIs(med, rf.ed)
        self.assertEqual('test', rf.name)
        self.assertEqual('test', rf.description)
        self.assertEqual("", rf.default)
        self.assertEqual('R', rf.type)
        self.assertDictEqual({}, rf.menu_dict)

    def test_is_a_ReporterFactory_instance(self):
        rf = RF(Mock(), 'test')
        self.assertIsInstance(rf, RRF)

    def test_create(self):
        """Create requester object"""
        rf = RF(Mock(), 'test')
        mock_extension = Mock()
        self.assertRaises(TypeError, rf.create)
        r = rf.create(mock_extension)
        self.assertIsInstance(r, R)
        self.assertIs(r.extension, mock_extension)
        self.assertIs(r.info, rf)


class TestRequester(unittest.TestCase):
    """Requester components perform asynchronous command. User application should override
    do_read() or use a runtime method set() to define the value. If do_read is present it will
    run in a new thread; when done value is updated and notified to scratch client application.
    For general behaviour look Reporter
    """

    def test_base(self):
        mock_e = Mock()  # Mock the extension
        mock_ed = Mock()  # Mock the extension definition

        """Costructor take extension as first argument and WaiterCommandFactory as second"""
        self.assertRaises(TypeError, R)
        self.assertRaises(TypeError, R, mock_e)

        rf = RF(ed=mock_ed, name="wait", description="Are you done?")
        r = R(mock_e, rf)
        self.assertIs(r.extension, mock_e)
        self.assertIs(r.info, rf)
        self.assertEqual("", r.value)
        self.assertEqual('wait', r.name)
        self.assertEqual('Are you done?', r.description)
        self.assertEqual('R', r.type)

    def test_is_Reporter_subclass(self):
        mock_e = Mock()  # Mock the extension
        mock_rf = MagicMock()  # Mock the request info
        r = R(mock_e, mock_rf)
        self.assertIsInstance(r, RR)

    def get_requester(self, name="requester", default=0, description=None, do_read=None):
        mock_e = Mock()
        return R.create(mock_e, name=name, default=default, description=description, do_read=do_read)

    def test_execute_busy_read_no_args(self):
        """Remove the busy argument even if there is an exception
        """
        r = self.get_requester()
        busy = 12345
        self.assertFalse(r.results)

        v = 12

        def do_read():
            return v

        r.do_read = do_read
        r.execute_busy_read(busy)
        self.assertEquals([(busy, v, None)], r.results)
        self.assertEqual(v, r.value)

        r._busy.add(busy)
        ex = Exception("my error")

        def do_read():
            raise ex

        r.do_read = do_read
        self.assertRaises(Exception, r.execute_busy_read, busy)
        self.assertEquals([(busy, v, None), (busy, "invalid", ex)], r.results)
        self.assertEqual(v, r.value)

    def test_execute_busy_read_one_arg(self):
        """Remove the busy argument even if there is an exception
        """
        r = self.get_requester(description="%n")
        busy = 12345
        self.assertFalse(r.results)

        v = 12

        def do_read(x):
            return v * x

        r.do_read = do_read
        r.execute_busy_read(busy, 2)
        self.assertEquals([(busy, v * 2, None)], r.results)
        self.assertDictEqual({2: 24}, r.value)

        r._busy.add(busy)
        ex = Exception("my error")

        def do_read(x):
            raise ex

        r.do_read = do_read
        self.assertRaises(Exception, r.execute_busy_read, busy, 3)
        self.assertEquals([(busy, 2 * v, None), (busy, "invalid", ex)], r.results)
        self.assertDictEqual({2: 24}, r.value)

    def test_execute_busy_read_two_args(self):
        """Check two args behaviour
        """
        r = self.get_requester(description="%n %n")
        busy = 12345
        self.assertFalse(r.results)

        v = 12

        def do_read(x, y):
            return v * (x + y)

        r.do_read = do_read
        r.execute_busy_read(busy, 2, 1)
        self.assertEquals([(busy, v * 3, None)], r.results)
        self.assertDictEqual({2: {1: 36}}, r.value)

    @patch("threading.RLock")
    def test_results_synchronize(self, m_lock):
        m_lock = m_lock.return_value
        r = self.get_requester()
        r.results
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)

    def test_get_results(self):
        r = self.get_requester()
        self.assertFalse(r.get_results())
        ex = [Exception(), Exception()]
        r._new_result(234, 12, None)
        r._new_result(24, 2, None)
        r._new_result(3324, "invalid", ex[0])
        r._new_result(324, "invalid", ex[1])
        vals = [(234, 12, None),
                (24, 2, None),
                (3324, "invalid", ex[0]),
                (324, "invalid", ex[1])]
        self.assertEquals(r.results, vals)
        self.assertEquals(r.get_results(),
                          vals)

        self.assertEqual(r.results, [])
        self.assertEqual(r.get_results(),
            [])
        with patch("threading.RLock") as m_lock:
            m_lock = m_lock.return_value
            r = self.get_requester()
            r.get_results()
            self.assertEqual(m_lock.mock_calls[0], call.__enter__())
            self.assertEqual(m_lock.mock_calls[-1], call.__exit__(None, None, None))

    def test_get_async_start_thread_to_execute_execute_busy_read_no_args(self):
        """Add busy, create thread with execute_busy_read target, set daemon to True and start thread.

        Just if component implement do_read()
        """
        r = self.get_requester()
        busy = 12345
        r.do_read = Mock()
        with patch("threading.Thread", autospec=True) as mock_thread_class:
            mock_thread = mock_thread_class.return_value
            r.get_async(busy)
            mock_thread_class.assert_called_with(name=ANY, target=r.execute_busy_read, args=(busy,))
            mock_thread.setDaemon.assert_called_with(True)
            self.assertTrue(mock_thread.start.called)
        """Sanity chack without mocks"""
        r.get_async(busy)

        """Without do_read"""
        del r.do_read
        with patch("threading.Thread", autospec=True) as mock_thread_class:
            r.get_async(busy)
            self.assertFalse(mock_thread_class.called)
        """Sanity chack without mocks"""
        r.get_async(busy)

    def test_get_async_start_thread_to_execute_execute_busy_read_two_args(self):
        """Check just args when build thread
        """
        r = self.get_requester(description="%n %n")
        busy = 12345
        r.do_read = Mock()
        with patch("threading.Thread", autospec=True) as mock_thread_class:
            mock_thread = mock_thread_class.return_value
            r.get_async(busy, 1, 2)
            mock_thread_class.assert_called_with(name=ANY, target=r.execute_busy_read, args=(busy, 1, 2))
        """Sanity chack without mocks"""
        r.get_async(busy, 2, 3)

        """Without do_read"""
        del r.do_read
        """Just sanity chack without mocks"""
        r.get_async(busy, 4, 5)

    def test_get_async_no_do_read_results_list_no_args(self):
        r = self.get_requester()
        self.assertFalse(r.results)
        busy = 12345
        r.get_async(busy)
        self.assertFalse(r.results)
        """set()"""
        r.set(223)
        self.assertEqual(r.results, [(busy, 223, None)])
        """two different busy"""
        r._flush_results()
        self.assertFalse(r.results)
        r.get_async(busy)
        r.get_async(busy + 1)
        r.set(233)
        self.assertEqual(r.results, [(busy, 233, None),
                                     (busy + 1, 233, None)])

        """same busy"""
        r._flush_results()
        self.assertFalse(r.results)
        r.get_async(busy)
        r.get_async(busy)
        r.set(333)
        self.assertEqual(r.results, [(busy, 333, None)])

        """Empty -> empty"""
        r._flush_results()
        r.set(433)
        self.assertFalse(r.results)

        """Reset clean state"""
        r.get_async(busy)
        r.reset()
        r.set(533)
        self.assertFalse(r.results)

    def test_get_async_no_do_read_results_list_one_arg(self):
        r = self.get_requester(description="%n")
        self.assertFalse(r.results)
        busy = 12345
        r.get_async(busy, 1)
        self.assertFalse(r.results)
        """set() on right arg"""
        r.set(223, 1)
        self.assertEqual(r.results, [(busy, 223, None)])
        """set() on other arg value"""
        r._flush_results()
        self.assertFalse(r.results)
        r.get_async(busy, 1)
        r.set(223, 2)
        self.assertFalse(r.results)
        """---and now the right value"""
        r.set(223, 1)
        self.assertEqual(r.results, [(busy, 223, None)])

        """two different busy on same args"""
        r._flush_results()
        self.assertFalse(r.results)
        r.get_async(busy, 1)
        r.get_async(busy + 1, 1)
        r.set(233, 1)
        self.assertEqual(r.results, [(busy, 233, None),
                                     (busy + 1, 233, None)])

        """two different busy on two arg"""
        r._flush_results()
        self.assertFalse(r.results)
        r.get_async(busy, 1)
        r.get_async(busy + 1, 2)
        r.set(233, 1)
        self.assertEqual(r.results, [(busy, 233, None)])
        r.set(234, 2)
        self.assertEqual(r.results, [(busy, 233, None),
                                     (busy + 1, 234, None)])

        """same busy same arg"""
        r._flush_results()
        self.assertFalse(r.results)
        r.get_async(busy, 1)
        r.get_async(busy, 1)
        r.set(333, 1)
        self.assertEqual(r.results, [(busy, 333, None)])

        """same busy not same arg"""
        r._flush_results()
        self.assertFalse(r.results)
        r.get_async(busy, 1)
        r.get_async(busy, 2)
        r.set(333, 1)
        self.assertEqual(r.results, [(busy, 333, None)])
        r.set(334, 2)
        self.assertEqual(r.results, [(busy, 333, None), (busy, 334, None)])

        """Empty -> empty"""
        r._flush_results()
        r.set(433, 1)
        self.assertFalse(r.results)

        """Reset clean state"""
        r.get_async(busy, 1)
        r.reset()
        r.set(533, 1)
        self.assertFalse(r.results)

    @patch("threading.RLock")
    def test_busy_access_synchronize(self, m_lock):
        m_lock = m_lock.return_value
        r = self.get_requester()
        r.busy
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)
        m_lock.reset_mock()

        def do_read():
            # Check busy add
            self.assertTrue(m_lock.__enter__.called)
            self.assertTrue(m_lock.__exit__.called)
            m_lock.reset_mock()

        r.do_read = do_read
        r.get_async(1234)

        def do_read():
            pass

        r.do_read = do_read
        m_lock.reset_mock()
        r.execute_busy_read(1234)
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)

    def test_reset(self):
        """Should reset busy set"""
        r = self.get_requester()
        ex = Exception("a")
        r._new_result(1234, 1, None)
        r._new_result(2234, 2, None)
        r._new_result(3234, "invalid", ex)
        self.assertEqual(r.results,
                         [(1234, 1, None),
                          (2234, 2, None),
                          (3234, "invalid", ex)])
        r.reset()
        self.assertEqual(r.results, [])

        with patch("threading.RLock") as m_lock:
            m_lock = m_lock.return_value
            """Must rebuild to hane the mock"""
            r = self.get_requester()
            r.reset()
            self.assertTrue(m_lock.__enter__.called)
            self.assertTrue(m_lock.__exit__.called)

    def test_get_cgi_no_arg(self):
        r = self.get_requester(name="My Name")
        self.assertIsNone(r.get_cgi("not your cgi"))
        self.assertIsNone(r.get_cgi("My%20Name"))
        """Must start by /"""
        """execute in line get() method"""
        cgi = r.get_cgi("/My%20Name")
        self.assertIsNotNone(cgi)
        with patch.object(r, "get_async", autospec=True) as mock_get_async, \
                patch.object(r, "busy_get", autospec=True) as mock_blockable_get:
            mock_blockable_get.return_value = 1232
            self.assertEqual("1232", cgi(Mock(path="My%20Name")))
            self.assertFalse(mock_get_async.called)

        """One argument that is an integer: call get_async"""
        self.assertIsNone(r.get_cgi("/My%20Name/mybusy"))
        cgi = r.get_cgi("/My%20Name/1234")
        self.assertIsNotNone(cgi)
        self.assertEqual({}, cgi.headers)
        with patch.object(r, "get_async", autospec=True) as mock_update:
            self.assertEqual("", cgi(Mock(path="My%20Name/3452")))
            mock_update.assert_called_with(3452)

    def test_get_cgi_one_int_arg(self):
        r = self.get_requester(name="My Name", description="%n")
        """No arg -> no answer"""
        self.assertIsNone(r.get_cgi("/My%20Name"))
        """Invalid arg -> None"""
        self.assertIsNone(r.get_cgi("/My%20Name/myarg"))
        """execute in line get() method"""
        cgi = r.get_cgi("/My%20Name/12")
        self.assertIsNotNone(cgi)
        with patch.object(r, "get_async", autospec=True) as mock_get_async, \
                patch.object(r, "busy_get", autospec=True) as mock_blockable_get:
            mock_blockable_get.return_value = 1232
            self.assertEqual("1232", cgi(Mock(path="My%20Name/12")))
            self.assertFalse(mock_get_async.called)

        """match int,int: call get_async"""
        self.assertIsNone(r.get_cgi("/My%20Name/mybusy/13"))
        cgi = r.get_cgi("/My%20Name/12/13")
        self.assertIsNotNone(cgi)
        self.assertEqual({}, cgi.headers)
        with patch.object(r, "get_async", autospec=True) as mock_get_async:
            self.assertEqual("", cgi(Mock(path="My%20Name/12/13")))
            mock_get_async.assert_called_with(12,13)

    def test_create(self):
        mock_e = Mock()
        r = R.create(mock_e, "requester")
        self.assertIs(mock_e, r.extension)
        self.assertEqual(r.name, "requester")
        self.assertEqual(r.type, "R")

        def do_read():
            return "goofy"

        r = R.create(mock_e, "requester2", default="RR", description="ASD", do_read=do_read)
        self.assertIs(mock_e, r.extension)
        self.assertEqual(r.name, "requester2")
        self.assertEqual(r.info.default, "RR")
        self.assertEqual(r.description, "ASD")
        self.assertEqual(r.get(), "goofy")
        self.assertEqual(r.type, "R")

    def test_poll(self):
        r = self.get_requester()
        self.assertDictEqual({}, r.poll())

    def test_busy_get_when_do_read_exist_no_arg(self):
        """Simply work like a proxy on do_read and not
        enter in condition context"""
        v = 51

        def do_read():
            return v

        r = self.get_requester(do_read=do_read)
        self.assertEqual(v, r.busy_get())
        v = 23
        self.assertEqual(v, r.busy_get())
        with patch.object(r, "_condition", autospec=True) as mock_condition:
            r.busy_get()
            self.assertFalse(mock_condition.__enter__.called)

    def test_busy_get_without_do_read_no_arg(self):
        """Execute busy_get() in a thread and check return value.
        Main cycle use set() to wake up thread"""
        r = self.get_requester()

        ex=[]

        def thread_body():
            try:
                self.assertEqual(123, r.busy_get())
            except Exception as e:
                ex.append(e)

        t = threading.Thread(target=thread_body)
        r._ready = set()
        t.start()
        with r._condition:
            r._condition.wait_for(lambda: () in r._ready, 0.1)
        r.set(123)  # Wakeup thread and do check
        t.join(0.2)
        self.assertFalse(t.isAlive())
        if ex:
            raise ex[0]

    def test_busy_get_without_do_read_some_args(self):
        """Execute busy_get() in a thread and check return value.
        Main cycle use set() to wake up thread"""
        r = self.get_requester(description="%n %n %s")

        ex=[]

        def thread_body():
            try:
                self.assertEqual(123, r.busy_get(12, 77, "minnie"))
            except Exception as e:
                ex.append(e)

        t = threading.Thread(target=thread_body)
        r._ready = set()
        args = (12, 77, "minnie")
        t.start()
        with r._condition:
            r._condition.wait_for(lambda: args in  r._ready, 0.1)
        r.set(123, 12, 77, "minnie")  # Wakeup thread and do check
        t.join(0.2)
        self.assertFalse(t.isAlive())
        if ex:
            raise ex[0]

        t = threading.Thread(target=thread_body)
        r._ready = set()
        t.start()
        with r._condition:
            r._condition.wait_for(lambda: args in r._ready, 0.1)
        r.set(123, 13, 77, "minnie")  # Don't wake up
        t.join(0.1)
        self.assertTrue(t.isAlive())
        r.set(123, 12, 77, "goofy")  # Don't wake up
        t.join(0.1)
        self.assertTrue(t.isAlive())
        r.set(123,12, 77, "minnie")  # Wakeup thread and do check
        t.join(0.2)
        self.assertFalse(t.isAlive())
        if ex:
            raise ex[0]

    def test_reset_unlock_waiter_request(self):
        """Execute busy_get().
        Main cycle use reset() to wake up thread.
        Then check if results is empty"""
        r = self.get_requester()
        r._new_result(1234, "a", None)
        self.assertTrue(r.results)
        # put something

        def thread_body():
            r.busy_get()

        t = threading.Thread(target=thread_body)
        r._ready = set()
        t.start()
        with r._condition:
            r._condition.wait_for(lambda: () in r._ready, 0.1)
        r.reset()  # Wakeup thread
        t.join(0.2)
        self.assertFalse(t.isAlive())
        self.assertSetEqual(set(), r._ready)
        self.assertFalse(r.results)


class TestBooleanBlock(unittest.TestCase):
    """BooleanBlock components Are just sensor that return boolean value (true if true , anything else otherwise)
    For general behaviour look Sensor
    """

    def test_base(self):
        mock_e = Mock()  # Mock the extension
        mock_ed = Mock()  # Mock the extension definition

        """Costructor take extension as first argument and WaiterCommandFactory as second"""
        self.assertRaises(TypeError, B)
        self.assertRaises(TypeError, B, mock_e)

        bf = BF(ed=mock_ed, name="ok", description="Are you done?")
        b = B(mock_e, bf)
        self.assertIs(b.extension, mock_e)
        self.assertIs(b.info, bf)
        self.assertEqual("", b.value)
        self.assertEqual('ok', b.name)
        self.assertEqual('Are you done?', b.description)
        self.assertEqual('b', b.type)

    def get_block(self, description="Are you done?", *args, **kwargs):
        bf = BF(ed=Mock(), name="ok", description=description, *args, **kwargs)
        return B(Mock(), bf)

    def test_is_Reporter_subclass(self):
        b = self.get_block()
        self.assertIsInstance(b, RR)

    def test_get_set_clear_simple(self):
        b = self.get_block()
        self.assertEqual("false", b.get())
        b.set(True)
        self.assertEqual("true", b.get())
        b.set(False)
        self.assertEqual("false", b.get())
        b.set("a")
        self.assertEqual("true", b.get())
        b.set("")
        self.assertEqual("false", b.get())
        b.set()
        self.assertEqual("true", b.get())
        b.clear()
        self.assertEqual("false", b.get())
        b.set("a")
        self.assertEqual("true", b.get())
        b.clear()
        self.assertEqual("false", b.get())

    def test_get_set_clear_one_arg(self):
        b = self.get_block(description="%m.ages", ages=[12, 13, 14])
        self.assertEqual("false", b.get(12))
        self.assertEqual("false", b.get(13))
        self.assertEqual("false", b.get(14))
        b.set(True, 12)
        self.assertEqual("true", b.get(12))
        self.assertEqual("false", b.get(13))
        self.assertEqual("false", b.get(14))
        b.set(True, 13)
        b.set(True, 14)
        self.assertEqual("true", b.get(12))
        self.assertEqual("true", b.get(13))
        self.assertEqual("true", b.get(14))
        b.set(False, 13)
        self.assertEqual("true", b.get(12))
        self.assertEqual("false", b.get(13))
        self.assertEqual("true", b.get(14))
        b.set("a", 13)
        self.assertEqual("true", b.get(13))
        b.set("", 13)
        self.assertEqual("false", b.get(13))

        b.set(True, 13)
        b.clear()
        self.assertEqual("false", b.get(12))
        self.assertEqual("false", b.get(13))
        self.assertEqual("false", b.get(14))

    def test_get_set_clear_two_args(self):
        b = self.get_block(description="%m.a %m.b", a=[1, 2], b=[3, 4])
        self.assertEqual("false", b.get(1, 3))
        self.assertEqual("false", b.get(1, 4))
        self.assertEqual("false", b.get(2, 3))
        self.assertEqual("false", b.get(2, 4))
        b.set(True, 1, 3)
        self.assertEqual("true", b.get(1, 3))
        self.assertEqual("false", b.get(1, 4))
        self.assertEqual("false", b.get(2, 3))
        self.assertEqual("false", b.get(2, 4))
        b.set(True, 2, 4)
        self.assertEqual("true", b.get(1, 3))
        self.assertEqual("false", b.get(1, 4))
        self.assertEqual("false", b.get(2, 3))
        self.assertEqual("true", b.get(2, 4))
        b.clear()
        self.assertEqual("false", b.get(1, 3))
        self.assertEqual("false", b.get(1, 4))
        self.assertEqual("false", b.get(2, 3))
        self.assertEqual("false", b.get(2, 4))


    def test_clear_default_True(self):
        b = self.get_block(default=True, description="%m.ages", ages=[12, 13, 14])
        self.assertEqual("true", b.get(12))
        self.assertEqual("true", b.get(13))
        self.assertEqual("true", b.get(14))
        b.clear()
        self.assertEqual("false", b.get(12))
        self.assertEqual("false", b.get(13))
        self.assertEqual("false", b.get(14))


    @patch("threading.RLock", autospec=True)
    def test_clear_synchronize(self, m_lock):
        m_lock = m_lock.return_value
        b = self.get_block()
        b.clear()
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)
        m_lock.reset_mock()
        b = self.get_block(description="%m.ages", ages=[12, 13, 14])
        b.clear()
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)

    def test_create(self):
        mock_e = Mock()
        b = B.create(mock_e, "bool")
        self.assertIs(mock_e, b.extension)
        self.assertEqual(b.name, "bool")
        self.assertEqual(b.type, "b")

        v = True

        def do_read():
            return v

        b = B.create(mock_e, "bool2", default=False, description="ASD", do_read=do_read)
        self.assertIs(mock_e, b.extension)
        self.assertEqual(b.name, "bool2")
        self.assertEqual(b.info.default, False)
        self.assertEqual(b.description, "ASD")
        self.assertEqual(b.get(), "true")
        self.assertEqual(b.type, "b")

        v = False
        self.assertEqual(b.get(), "false")


class TestBooleanFactory(unittest.TestCase):
    """We are testing boolean descriptors (reporters that return boolean). They define name and description."""

    def test_base(self):
        """Costructor take ExtensionDefinition as first argument and name as second"""
        med = Mock()
        self.assertRaises(TypeError, BF)
        self.assertRaises(TypeError, BF, med)
        bf = BF(med, 'test')
        self.assertIs(med, bf.ed)
        self.assertEqual('test', bf.name)
        self.assertEqual('test', bf.description)
        self.assertEqual('', bf.default)
        self.assertEqual('b', bf.type)
        self.assertDictEqual({}, bf.menu_dict)

    def test_is_a_ReporterFactory_instance(self):
        bf = BF(Mock(), 'test')
        self.assertIsInstance(bf, RRF)

    def test_create(self):
        """Create requester object"""
        bf = BF(Mock(), 'test')
        mock_extension = Mock()
        self.assertRaises(TypeError, bf.create)
        b = bf.create(mock_extension)
        self.assertIsInstance(b, B)
        self.assertIs(b.extension, mock_extension)
        self.assertIs(b.info, bf)


class Test_utils(unittest.TestCase):
    """Testing useful functions"""

    def test_to_bool(self):
        self.assertIs(True, to_bool("true"))
        self.assertIs(True, to_bool("True"))
        self.assertIs(True, to_bool("tRUe"))
        self.assertIs(False, to_bool("tRU"))
        self.assertIs(False, to_bool("false"))
        self.assertIs(False, to_bool("False"))
        self.assertIs(False, to_bool(""))
        self.assertIs(False, to_bool("1"))
        self.assertIs(False, to_bool("Yes"))
        self.assertIs(False, to_bool("0"))

    def test_parse_description_base(self):
        """Signature : take one positional argument (the description to parse) and optional nominal arguments
        that are the menues"""
        self.assertRaises(TypeError, parse_description)
        self.assertRaises(TypeError, parse_description, "a", "b")
        self.assertEqual((), parse_description(""))
        self.assertEqual((), parse_description("Minnie"))
        self.assertEqual((str,), parse_description("Minnie %s"))
        self.assertEqual((str, float, to_bool), parse_description("Minnie %s from value %n is %b"))


    def test_parse_description_menu(self):
        """Add some menues"""
        self.assertEqual((), parse_description("Minnie %m", wrong_menu=["a", "b"]))

        self.assertRaises(TypeError, parse_description, "Minnie %m.my_menu")

        my_menu = ["a", "b"]
        d = parse_description("Minnie %m.my_menu", my_menu=my_menu)
        self.assertEqual(1, len(d))
        self.assertIsNotNone(d[0])
        for e in my_menu:
            self.assertEqual(d[0](e), e)
        self.assertRaises(KeyError, d[0], "not in my_menu")
        self.assertRaises(KeyError, d[0], 0)
        my_other_menu = ["1", "2", "3"]
        d = parse_description("Minnie %m.my_menu and %m.my_other_menu", my_menu=my_menu, my_other_menu=my_other_menu)
        self.assertEqual(2, len(d))
        self.assertIsNotNone(d[0])
        self.assertIsNotNone(d[1])
        for e in my_other_menu:
            self.assertEqual(d[1](e), e)
        self.assertRaises(KeyError, d[1], "not in my_menu")
        self.assertRaises(KeyError, d[1], 0)

        """Menu name can end by . """
        my_menu = ["a", "b"]
        d = parse_description("Minnie %m.my_menu.", my_menu=my_menu)
        self.assertEqual(1, len(d))
        self.assertIsNotNone(d[0])
        for e in my_menu:
            self.assertEqual(d[0](e), e)

        """Not valid menu"""
        self.assertRaises(TypeError, parse_description, "Minnie %m.my_menu", my_menu=123)


    def test_parse_description_menu_mapper(self):
        """If the requester menu is a mapper elements return the mapped object instead the key"""
        my_menu = {"a": "A", "b": "B"}
        d = parse_description("Minnie %m.my_menu", my_menu=my_menu)
        self.assertEqual(1, len(d))
        self.assertIsNotNone(d[0])
        self.assertEqual(d[0]("a"), "A")
        self.assertEqual(d[0]("b"), "B")
        self.assertRaises(KeyError, d[0], "not in my_menu")

    def test_parse_description_editable_menu(self):
        """For editable menu if not given as keyword args it will raise TypeError.
        Otherwise the menu could be a mapper object or a list/tuple. If it is a mapper it should map None value
        that can be a
         - value that will replace original value
         - a callable that will by called by the value and return the valid one
         If None me is not present for the non mapped object we will use str()
         If menu is a list, set or tuple the element str() function will be used for all elements
         """
        """No menu case -> TypeError"""
        self.assertRaises(TypeError, parse_description, "Minnie %d.my_menu")

        """No None element -> default str"""
        my_menu = {"a": "A", "b": "B"}
        d = parse_description("Minnie %d.my_menu", my_menu=my_menu)
        self.assertEqual(1, len(d))
        self.assertIsNotNone(d[0])
        self.assertEqual(d[0]("a"), "A")
        self.assertEqual(d[0]("b"), "B")
        self.assertEqual(d[0]("c"), "c")
        self.assertEqual(d[0](1), "1")
        self.assertEqual(d[0](1.2), "1.2")
        my_menu = {"a": "A", "b": "B", None: lambda v: str(v).upper()}
        d = parse_description("Minnie %d.my_menu", my_menu=my_menu)
        self.assertEqual(1, len(d))
        self.assertIsNotNone(d[0])
        self.assertEqual(d[0]("a"), "A")
        self.assertEqual(d[0]("b"), "B")
        self.assertEqual(d[0]("c"), "C")
        self.assertEqual(d[0]("d"), "D")
        self.assertEqual(d[0](1), "1")
        self.assertEqual(d[0](1.2), "1.2")

        my_menu = ["a", "b"]
        d = parse_description("Minnie %d.my_menu", my_menu=my_menu)
        self.assertEqual(1, len(d))
        self.assertIsNotNone(d[0])
        self.assertEqual(d[0]("a"), "a")
        self.assertEqual(d[0]("b"), "b")
        self.assertEqual(d[0]("c"), "c")
        self.assertEqual(d[0]("d"), "d")
        self.assertEqual(d[0](1), "1")
        self.assertEqual(d[0](1.2), "1.2")

        """Menu name can end by . """
        my_menu = ["a", "b"]
        d = parse_description("Minnie %d.my_menu.", my_menu=my_menu)
        self.assertEqual(1, len(d))
        self.assertIsNotNone(d[0])
        for e in my_menu:
            self.assertEqual(d[0](e), e)

        """Not valid menu"""
        self.assertRaises(TypeError, parse_description, "Minnie %d.my_menu", my_menu=123)

    def test_parse_description_elements(self):
        """Function in parsed descriptions must can have elements property that return a
        set of elements in menu if applicable, raise AttributeError otherwise"""
        d = parse_description("val %n string %s bool %b menu %m.my_menu and editable %d.my_other_menu",
                              my_menu=["a", "b"], my_other_menu=["c", "d"])
        self.assertRaises(AttributeError, lambda e: e.elements, d[0])
        self.assertRaises(AttributeError, lambda e: e.elements, d[1])
        self.assertRaises(AttributeError, lambda e: e.elements, d[2])
        self.assertSetEqual({"a", "b"}, d[3].elements)
        self.assertSetEqual({"c", "d"}, d[4].elements)

        d = parse_description("val %n string %s bool %b menu %m.my_menu and editable %d.my_other_menu",
                              my_menu={"a": "A", "b": "B"}, my_other_menu={"c": "C", "d": "D"})
        self.assertRaises(AttributeError, lambda e: e.elements, d[0])
        self.assertRaises(AttributeError, lambda e: e.elements, d[1])
        self.assertRaises(AttributeError, lambda e: e.elements, d[2])
        self.assertSetEqual({"a", "b"}, d[3].elements)
        self.assertSetEqual({"c", "d"}, d[4].elements)


class TestReporter(unittest.TestCase):
    """Reporter are sensor blocks that support arguments"""

    def test_base(self):
        mock_e = Mock()  # Mock the extension
        mock_ed = Mock()  # Mock the extension definition

        """Costructor take extension as first argument and ReporterFactory as second"""
        self.assertRaises(TypeError, RR)
        self.assertRaises(TypeError, RR, mock_e)

        rrf = RRF(ed=mock_ed, name="get_message", description="Get message from %s")
        rr = RR(mock_e, rrf)
        self.assertIs(rr.extension, mock_e)
        self.assertIs(rr.info, rrf)
        self.assertEqual({}, rr.value)
        self.assertEqual('get_message', rr.name)
        self.assertEqual('Get message from %s', rr.description)
        self.assertEqual('r', rr.type)

    def test_proxy(self):
        """Check the proxy"""
        mock_e = Mock()  # Mock the extension
        mock_rf = MagicMock()  # Mock the reporter info
        r = RR(mock_e, mock_rf)
        self.assertIs(r.type, mock_rf.type)
        self.assertIs(r.name, mock_rf.name)
        self.assertIs(r.description, mock_rf.description)
        self.assertIs(r.definition, mock_rf.definition)
        self.assertIs(r.signature, mock_rf.signature)

    def test_get_should_respect_the_signature(self):
        mock_e = Mock()  # Mock the extension
        med = Mock()
        rrf = RRF(med, 'test', description="Base Signature: no args")
        r = RR(mock_e, rrf, value=13)
        self.assertEqual(13, r.get())
        self.assertRaises(TypeError, r.get, 1)
        self.assertRaises(TypeError, r.get, "minnie")

        """One string"""
        rrf = RRF(med, 'test', description="Get info about %s")
        r = RR(mock_e, rrf, value={None: "my default", "sentinel": "you got it"})
        self.assertRaises(TypeError, r.get)
        self.assertRaises(TypeError, r.get, "first", "second")
        self.assertEqual("you got it", r.get("sentinel"))
        self.assertEqual("my default", r.get("wrong"))
        self.assertEqual("my default", r.get(12))
        self.assertEqual("my default", r.get("32.4"))
        self.assertEqual("my default", r.get(3.4))

        """One string, one float, one menu"""
        rrf = RRF(med, 'test', description="Get info about %s, age %n, gender %m.gender", gender=["male", "female"])
        r = RR(mock_e, rrf, value={None: "my default", "sentinel": {None: "default age",
                                                                    32: {"male": "MALE", "female": "FEMALE"},
                                                                    12: {"male": "MalE"}}})

        self.assertRaises(TypeError, r.get)
        self.assertRaises(TypeError, r.get, "first")
        self.assertRaises(TypeError, r.get, "first", 2)
        self.assertRaises(TypeError, r.get, "first", 2, "male", "other")

        self.assertEqual("MALE", r.get("sentinel", 32, "male"))
        self.assertEqual("FEMALE", r.get("sentinel", 32, "female"))
        self.assertEqual("MalE", r.get("sentinel", 12, "male"))
        self.assertEqual("default age", r.get("sentinel", 12, "female"))  # last default
        self.assertEqual("default age", r.get("sentinel", 5, "female"))  # age default
        self.assertEqual("my default", r.get("sent", 12, "male"))  # name default

        self.assertRaises(TypeError, r.get, "sentinel", 32, "MALE")

    def test_set_should_respect_the_signature(self):
        mock_e = Mock()  # Mock the extension
        med = Mock()
        rrf = RRF(med, 'test', description="Base Signature: no args")
        r = RR(mock_e, rrf, value=13)
        r.set(12)
        self.assertRaises(TypeError, r.set, 10, 1)
        self.assertRaises(TypeError, r.set, 11, "minnie")

        """One string"""
        rrf = RRF(med, 'test', description="Get info about %s")
        r = RR(mock_e, rrf, value={None: "my default", "sentinel": "you got it"})
        self.assertRaises(TypeError, r.set, "No info")
        self.assertRaises(TypeError, r.set, "No info", "john", "other")
        r.set("No info", "john")
        self.assertEqual("you got it", r.get("sentinel"))
        self.assertEqual("No info", r.get("john"))
        self.assertEqual("my default", r.get("wrong"))
        self.assertEqual("my default", r.get(12))
        self.assertEqual("my default", r.get("32.4"))
        self.assertEqual("my default", r.get(3.4))

        """One string, one float, one menu"""
        rrf = RRF(med, 'test', description="Get info about %s, age %n, gender %m.gender", gender=["male", "female"])
        r = RR(mock_e, rrf, value={None: "my default", "sentinel": {None: "default age",
                                                                    32: {"male": "MALE", "female": "FEMALE"},
                                                                    12: {"male": "MalE"}}})

        self.assertRaises(TypeError, r.set)
        self.assertRaises(TypeError, r.set, "GOLD", "first")
        self.assertRaises(TypeError, r.set, "GOLD", "first", 2)
        self.assertRaises(TypeError, r.set, "GOLD", "first", 2, "male", "other")

        r.set("GOLD", "john", 25, "male")
        self.assertEqual("GOLD", r.get("john", 25, "male"))
        self.assertEqual("MALE", r.get("sentinel", 32, "male"))
        # Override
        r.set("MaLe", "sentinel", 32, "male")
        self.assertEqual("MaLe", r.get("sentinel", 32, "male"))

        self.assertRaises(TypeError, r.set, "GOLD", "sentinel", 32, "MALE")

    def test_reset_recover_default_value(self):
        mock_e = Mock()  # Mock extension
        rrf = RRF(mock_e, 'test', description="menu 1 %m.menu1 menu 2 %m.menu2", menu1=["a", "b"], menu2=["c", "d"])
        r = RR(mock_e, rrf)
        orig_d = {k: {j: "" for j in ["c", "d"]} for k in ["a", "b"]}

        d = copy.deepcopy(orig_d)
        orig_results = {(k, j): "" for k in ["a", "b"] for j in ["c", "d"]}
        results = orig_results.copy()
        self.assertDictEqual(d, r.value)
        self.assertDictEqual(results, r.poll())
        r.set(33, "a", "c")
        d["a"]["c"] = results[("a", "c")] = 33
        self.assertDictEqual(d, r.value)
        self.assertDictEqual(results, r.poll())
        r.reset()
        self.assertDictEqual(orig_d, r.value)
        self.assertDictEqual(orig_results, r.poll())

        """No trivial default"""
        rrf = RRF(mock_e, 'test', default={None: 45, "a": {"d": 30}, "b": {None: 19}},
                  description="menu 1 %m.menu1 menu 2 %m.menu2", menu1=["a", "b"], menu2=["c", "d"])
        r = RR(mock_e, rrf)
        orig_d = {"a": {"c": 45, "d": 30}, "b": {"c": 19, "d": 19}}
        d = copy.deepcopy(orig_d)
        orig_results = {("a", "c"): 45,
                        ("a", "d"): 30,
                        ("b", "c"): 19,
                        ("b", "d"): 19,
        }
        results = orig_results.copy()
        self.assertDictEqual(d, r.value)
        self.assertDictEqual(results, r.poll())
        r.set(-3, "a", "c")
        d["a"]["c"] = results[("a", "c")] = -3
        self.assertDictEqual(d, r.value)
        self.assertDictEqual(results, r.poll())
        r.reset()
        self.assertDictEqual(orig_d, r.value)
        self.assertDictEqual(orig_results, r.poll())

    def test_do_read(self):
        mock_e = Mock()  # Mock the extension
        rrf = RRF(mock_e, 'test', description="Base")
        r = RR(mock_e, rrf)
        r.set("ss")
        self.assertEqual("ss", r.get())
        r.do_read = lambda: "AA"
        self.assertEqual("AA", r.get())

        """Change Signature"""
        rrf = RRF(mock_e, 'test', description="menu %m.gender", gender=["male", "female"])
        r = RR(mock_e, rrf)
        r.do_read = lambda g: g.upper()
        self.assertEqual("MALE", r.get("male"))
        self.assertDictEqual({"male": "MALE", "female": ""}, r.value)
        """Raise exception wrong signature"""
        r.do_read = lambda: "NO CALL"
        self.assertRaises(TypeError, r.get, "male")
        r.do_read = lambda a, b: "NO CALL"
        self.assertRaises(TypeError, r.get, "male")
        """Don't mask exception"""

        def _raise(a):
            raise Exception(a)

        r.do_read = _raise
        self.assertRaises(Exception, r.get, "male")

        "Respect float"
        rrf = RRF(mock_e, 'test', description="number %n")
        r = RR(mock_e, rrf)
        r.do_read = lambda a: a * 2
        self.assertEqual(1.2, r.get(0.6))
        self.assertEqual(1.2, r.get("0.6"))
        self.assertEqual(2.0, r.get(1))


    @patch("threading.RLock", autospec=True)
    def test_get_and_set_synchronize(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock extension
        mock_rf = MagicMock()  # Mock reporter info
        r = RR(mock_e, mock_rf, value=56)
        r.get()
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)
        m_lock.reset_mock()
        r.set("ss")
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)
        m_lock.reset_mock()

        """Change signature"""
        mock_rf.signature = (float, str)
        r = RR(mock_e, mock_rf, value={})
        r.get(1.0, "Robert")
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)
        m_lock.reset_mock()
        r.set("ss", 1.0, "Robert")

    def test_value(self):
        """1) return last computed value
           1-a) if signature is empty return value
           1-b) return a dictionary of resolved result
           2) synchronize
        """
        mock_e = Mock()  # Mock extension
        mock_rf = MagicMock()  # Mock reporter info
        r = RR(mock_e, mock_rf, value=56)
        self.assertEqual(56, r.value)
        r.set("ss")
        self.assertEqual("ss", r.value)

        """Simple case: one menue exstension"""
        rrf = RRF(mock_e, 'test', description="Numbers of %m.gender", gender=["male", "female"])
        vals = {"male": 12, "female": 32}
        r = RR(mock_e, rrf, value=vals)
        self.assertDictEqual(vals, r.value)
        """Must be a copy"""
        v = r.value
        v["male"] = 1
        self.assertEqual(vals["male"], 12)
        self.assertDictEqual(vals, r.value)

        rrf = RRF(mock_e, 'test', description="Numbers of %m.gender from %m.state", gender=["male", "female"],
                  state=["Italy", "USA", "Germany"])
        r = RR(mock_e, rrf, value=21)
        d = {k: {j: 21 for j in ["Italy", "USA", "Germany"]} for k in ["male", "female"]}
        self.assertDictEqual(d, r.value)

        rrf = RRF(mock_e, 'test', description="Numbers of %d.gender from %d.state", gender=["male", "female"],
                  state=["Italy", "USA", "Germany"])
        r = RR(mock_e, rrf, value={"male": {None: 33}, "female": {"USA": 11, None: 44}, None: 1})
        d = {"male": {j: 33 for j in ["Italy", "USA", "Germany"]}}
        d["female"] = {j: 44 for j in ["Italy", "Germany"]}
        d["female"]["USA"] = 11
        self.assertDictEqual(d, r.value)
        r.set(77, "male", "Italy")
        d["male"]["Italy"] = 77
        self.assertDictEqual(d, r.value)
        r.set(99, "unknown", "French")

        d["unknown"] = {j: 1 for j in ["Italy", "USA", "Germany"]}
        d["unknown"]["French"] = 99

        self.assertDictEqual(d, r.value)

        rrf = RRF(mock_e, 'test', description="string %s menu %m.gender", gender=["male", "female"])
        r = RR(mock_e, rrf, value=55)
        self.assertDictEqual({}, r.value)
        r.set(12, "test", "male")
        self.assertDictEqual({"test": {"male": 12, "female": 55}}, r.value)

        with patch("threading.RLock") as m_lock:
            m_lock = m_lock.return_value
            """We must rebuild s to mock lock"""
            r = RR(mock_e, rrf, value=75)
            r.value
            self.assertTrue(m_lock.__enter__.called)
            self.assertTrue(m_lock.__exit__.called)
            m_lock.reset_mock()
            r._set_value(32, "test", "female")
            self.assertTrue(m_lock.__enter__.called)
            self.assertTrue(m_lock.__exit__.called)

    def test_get_cgi(self):
        """Standard description with o arguments"""
        mock_e = Mock()  # Mock extension
        rrf = RRF(mock_e, 'My Name', description="Base")
        r = RR(mock_e, rrf)
        self.assertIsNone(r.get_cgi("not your cgi"))
        self.assertIsNone(r.get_cgi("My%20Name"))
        """Must start by /"""
        """execute in line get() method"""
        cgi = r.get_cgi("/My%20Name")
        self.assertIsNotNone(cgi)
        r.do_read = lambda: 54321
        self.assertEqual("54321", cgi(Mock(path="My%20Name")))

        """More args return None"""
        self.assertIsNone(r.get_cgi("/My%20Name/1234"))

        rrf = RRF(mock_e, 'My Name', description="string %s number %n boolean %b menu %m.menu editable menu %d.ed_menu",
                  menu=["a", "b"], ed_menu=["c", "d"])
        r = RR(mock_e, rrf)
        self.assertIsNone(r.get_cgi("/My%20Name"))
        self.assertIsNone(r.get_cgi("/My%20Name/test"))
        self.assertIsNone(r.get_cgi("/My%20Name/test/1.2"))
        self.assertIsNone(r.get_cgi("/My%20Name/test/1.2/true"))
        self.assertIsNone(r.get_cgi("/My%20Name/test/1.2/true/a"))
        cgi = r.get_cgi("/My%20Name/test/1.2/true/a/k")
        self.assertIsNotNone(cgi)
        r.do_read = lambda *args: ",".join(map(str, args))
        self.assertEqual("test,1.2,True,a,k", cgi(Mock(path="My%20Name/test/1.2/true/a/k")))
        self.assertIsNone(r.get_cgi("/My%20Name/test/aa/true/a/d"))
        self.assertIsNone(r.get_cgi("/My%20Name/test/1/false/d/d"))

    def test_create(self):
        mock_e = Mock()
        r = RR.create(mock_e, "reporter")
        self.assertIs(mock_e, r.extension)
        self.assertEqual(r.name, "reporter")

        def do_read():
            return "goofy"

        r = RR.create(mock_e, "reporter2", default="S", description="No Args", do_read=do_read)
        self.assertIs(mock_e, r.extension)
        self.assertEqual(r.name, "reporter2")
        self.assertEqual(r.info.default, "S")
        self.assertEqual(r.description, "No Args")
        self.assertEqual(r.get(), "goofy")

        """Wrong do_read() signature"""
        self.assertRaises(TypeError, RR.create, mock_e, "reporter2", default="S", description="string %s",
                          do_read=do_read)

        def do_read(v):
            return v.upper()

        r = RR.create(mock_e, "reporter2", default="S", description="string %s", do_read=do_read)
        self.assertEqual(r.get("goofy"), "GOOFY")

    def test_poll_base(self):
        """Standard description with o arguments"""
        mock_e = Mock()  # Mock extension
        rrf = RRF(mock_e, 'test', description="Base")
        r = RR(mock_e, rrf)
        self.assertDictEqual({(): ''}, r.poll())
        r = RR(mock_e, rrf, value=32)
        self.assertDictEqual({(): 32}, r.poll())
        r.set(88)
        self.assertDictEqual({(): 88}, r.poll())
        v = 99
        r.do_read = lambda: v
        self.assertDictEqual({(): 99}, r.poll())
        v = 77
        self.assertDictEqual({(): 77}, r.poll())

    def test_poll_menues(self):
        mock_e = Mock()  # Mock extension
        rrf = RRF(mock_e, 'test', description="menu 1 %m.menu1 menu 2 %m.menu2", menu1=["a", "b"], menu2=["c", "d"])
        r = RR(mock_e, rrf)
        self.assertDictEqual({(k, j): "" for k in ["a", "b"] for j in ["c", "d"]}, r.poll())
        r = RR(mock_e, rrf, value=32)
        d = {(k, j): 32 for k in ["a", "b"] for j in ["c", "d"]}
        self.assertDictEqual(d, r.poll())
        r.set(1, "a", "d")
        d[("a", "d")] = 1
        self.assertDictEqual(d, r.poll())
        v = 99
        r.do_read = lambda a, b: v
        """Don't call do_read()"""
        self.assertDictEqual(d, r.poll())
        """get() call do_read()"""
        r.get("b", "c")
        d[("b", "c")] = 99
        self.assertDictEqual(d, r.poll())

    def test_poll_other(self):
        mock_e = Mock()  # Mock extension
        rrf = RRF(mock_e, 'test', description="string %s number %n boolean %b")
        r = RR(mock_e, rrf)
        self.assertDictEqual({}, r.poll())
        r.set(2, "val", 1.2, True)
        self.assertDictEqual({('val', 1.2, True): 2}, r.poll())
        r.set(7, "val", 2.2, False)
        self.assertDictEqual({('val', 1.2, True): 2, ('val', 2.2, False): 7}, r.poll())


class TestReporterFactory(unittest.TestCase):
    """We are testing reporter descriptors (sensor with arguments). They define name and description and provide
    a signature: a tuple of functions that take the arguments as string and return the arguments to use
    in do_read() and set() methods."""

    def test_base(self):
        """Costructor take ExtensionDefinition as first argument and name as second"""
        med = Mock()
        self.assertRaises(TypeError, RRF)
        self.assertRaises(TypeError, RRF, med)
        rrf = RRF(med, 'test')
        self.assertIs(med, rrf.ed)
        self.assertEqual('test', rrf.name)
        self.assertEqual('test', rrf.description)
        self.assertEqual("", rrf.default)
        self.assertEqual('r', rrf.type)
        self.assertDictEqual({}, rrf.menu_dict)

    def apply_signature(self, sig, values):
        return [f(v) for f, v in zip(sig, values)]

    def test_signature(self):
        """Return the signature of do_read() and set() method. To do the work use parse_description"""
        med = Mock()
        rrf = RRF(med, 'test', description="Give me %n fingers from %m.hands. Its name is %s", hands=["left", "right"])
        vals = self.apply_signature(rrf.signature, ("3", "left", "joe"))
        self.assertEqual(vals, [3, "left", "joe"])

        rrf = RRF(med, 'test', description="Give me %n fingers from %m.hands. Its name is %s",
                  hands={"left": 0, "right": 1})
        vals = self.apply_signature(rrf.signature, ("3", "left", "joe"))
        self.assertEqual(vals, [3, 0, "joe"])
        vals = self.apply_signature(rrf.signature, ("5.2", "right", "Ely"))
        self.assertEqual(vals, [5.2, 1, "Ely"])

        """Change a dict must not change behaviour"""
        m = {"left": 0, "right": 1}
        rrf = RRF(med, 'test', description="Give me %n fingers from %m.hands. Its name is %s", hands=m)
        vals = self.apply_signature(rrf.signature, ("1", "right", "Vincent"))
        self.assertEqual(vals, [1, 1, "Vincent"])
        m["right"] = 32
        vals = self.apply_signature(rrf.signature, ("1", "right", "Vincent"))
        self.assertEqual(vals, [1, 1, "Vincent"])

    def test_create(self):
        """Create the reporter object"""
        rrf = RRF(Mock(), 'test')
        mock_extension = Mock()
        self.assertRaises(TypeError, rrf.create)
        r = rrf.create(mock_extension, 1345)
        self.assertIsInstance(r, RR)
        self.assertIs(r.extension, mock_extension)
        self.assertIs(r.info, rrf)
        self.assertEqual(r.get(), 1345)

        rrf = RRF(Mock(), 'test', description="string %s")
        r = rrf.create(mock_extension)
        self.assertIsInstance(r, RR)
        self.assertIs(r.extension, mock_extension)
        self.assertIs(r.info, rrf)
        self.assertEqual(r.get("www"), "")
        r.do_read = lambda v: v.upper()
        self.assertEqual(r.get("www"), "WWW")

    def test_menus(self):
        med = Mock()
        rrf = RRF(med, 'test', description="%m.hands", hands=["left", "right"])
        self.assertDictEqual({"hands": ["left", "right"]}, rrf.menus)

        """Pay attentiontion to mappers"""
        rrf = RRF(med, 'test', description="%m.hands", hands={"Left": "left", "Right": "right"})
        self.assertDictEqual({"hands": ["Left", "Right"]}, rrf.menus)


if __name__ == '__main__':
    unittest.main()
