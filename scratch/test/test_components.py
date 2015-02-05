from mock import ANY

__author__ = 'michele'

import unittest
from scratch.portability.mock import patch, Mock
from scratch.components import Sensor as S, SensorFactory as SF, \
    Command as C, CommandFactory as CF, HatFactory as HF, Hat as H, \
    WaiterCommand as W, WaiterCommandFactory as WF


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

    @patch("threading.Lock")
    def test_reset_synchronize(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock the extension
        mock_sf = Mock()  # Mock the sensor info
        s = S(mock_e, mock_sf)
        """just call s.reset()"""
        s.reset()
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)


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
    def test_command_and_value_synchronize(self, m_lock):
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

    @patch("threading.Lock")
    def test_reset_synchronize(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock the extension
        mock_cf = Mock()  # Mock the command info
        c = C(mock_e, mock_cf)
        """just call c.reset()"""
        c.reset()
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)

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
        c.command("a", "b")
        self.assertEqual(v[-1], ("a", "b"))


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
        mock_hf = Mock()  # Mock the command info
        h = H(mock_e, mock_hf)
        self.assertIs(h.type, mock_hf.type)
        self.assertIs(h.name, mock_hf.name)
        self.assertIs(h.description, mock_hf.description)
        self.assertIs(h.definition, mock_hf.definition)

    def test_flag(self):
        mock_e = Mock()  # Mock the extension
        mock_hf = Mock()  # Mock the command info
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

    @patch("threading.Lock")
    def test_flag_and_state_synchronize_do_flag_no(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock the extension
        mock_hf = Mock()  # Mock the hat info
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
        mock_hf = Mock()  # Mock the hat info
        h = H(mock_e, mock_hf)
        """call h.reset() and check i f flag reset"""
        h.flag()
        h.reset()
        self.assertFalse(h.state)

    @patch("threading.Lock")
    def test_reset_synchronize(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock the extension
        mock_hf = Mock()  # Mock the hat info
        h = H(mock_e, mock_hf)
        h.reset()
        self.assertTrue(m_lock.__enter__.called)
        self.assertTrue(m_lock.__exit__.called)

    def test_get_cgi(self):
        mock_e = Mock()  # Mock the extension
        mock_hf = Mock()  # Mock the hat info
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
        mock_cf = Mock()  # Mock the command info
        w = W(mock_e, mock_cf)
        self.assertIsInstance(w, C)

    def test_execute_busy_command(self):
        """Remove the busy argument even if there is an exception
        """
        mock_e = Mock()  # Mock the extension
        mock_cf = Mock()  # Mock the command info
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
        mock_cf = Mock()  # Mock the command info
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

    @patch("threading.Lock")
    def test_busy_access_synchronize(self, m_lock):
        m_lock = m_lock.return_value
        mock_e = Mock()  # Mock the extension
        mock_cf = Mock()  # Mock the sensor info
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
        mock_cf = Mock()  # Mock the sensor info
        w = W(mock_e, mock_cf)
        w._busy_add(1234)
        w._busy_add(2234)
        w._busy_add(3234)
        self.assertSetEqual(w.busy, {1234, 2234, 3234})
        w.reset()
        self.assertSetEqual(w.busy, set())

        with patch("threading.Lock") as m_lock:
            m_lock = m_lock.return_value
            """Must rebuild to hane the mock"""
            w = W(mock_e, mock_cf)
            w.reset()
            self.assertTrue(m_lock.__enter__.called)
            self.assertTrue(m_lock.__exit__.called)

    def test_get_cgi(self):
        mock_e = Mock()  # Mock the extension
        mock_wf = Mock()  # Mock the waiter command info
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
        w.command("a", "b")
        self.assertEqual(v[-1], ("b",))


if __name__ == '__main__':
    unittest.main()
