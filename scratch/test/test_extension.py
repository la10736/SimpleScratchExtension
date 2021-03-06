import http
import socketserver
import time
import scratch

__author__ = 'michele'
import unittest
from scratch.portability.mock import patch, Mock, PropertyMock, MagicMock
from scratch.extension import ExtensionDefinition as ED, render_args
from scratch.extension import Extension as E
from scratch.extension import ExtensionService as ES, EXTENSION_DEFAULT_PORT, EXTENSION_DEFAULT_ADDRESS
from scratch.extension import ExtensionBase as EB
from scratch.extension import ExtensionServiceBase as EBS
from scratch.components import CommandFactory, Sensor, HatFactory


class TestExstensionDefinition(unittest.TestCase):
    """Definisce una estensione con un nome, una descrizione
    es i descrittori dei singoli componenti.
    Si tratta di oggetti che poi vengono passati ai costruttori di estensioni.
    """

    def setUp(self):
        """Clean all registered descriptions"""
        ED._unregister_all()

    def test_base(self):
        ed = ED("goofy")
        self.assertIsNotNone(ed)
        self.assertEqual("goofy", ed.name)
        self.assertEqual("goofy", ed.description)
        self.assertRaises(TypeError, ES)
        """Nominali"""
        e = ED(description="donald duck and goofy", name="donald duck")
        self.assertEqual(("donald duck", "donald duck and goofy"), (e.name, e.description))

    def test_name(self):
        """Deve essere unico"""
        ed = ED("donald duck")
        self.assertRaises(ValueError, ED, "donald duck")

    def test_registered(self):
        ED("again")
        ED("again again")
        self.assertSetEqual({"again", "again again"}, ED.registered())

    def test_get_registered(self):
        a = ED("again")
        aa = ED("again again")
        self.assertIs(a, ED.get_registered("again"))
        self.assertIs(aa, ED.get_registered("again again"))
        self.assertRaises(KeyError, ED.get_registered, "goofy")

    def test__register_components(self):
        """Verificare che il componente venga registrato nell'insimeme dei componenti usando
        la property."""
        e = ED("es")
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
        self.assertSetEqual({c, d}, set(e.components))
        """Register components prende anche piu' di un elemento"""
        f, g, h, i = (Mock() for _ in range(4))
        e._register_components(f, g, h, i)
        self.assertSetEqual({c, d, f, g, h, i}, set(e.components))

        """deve dare eccezione se il componente NON ha l'attributo name"""
        c = Mock()
        del c.name
        self.assertRaises(TypeError, e._register_components, c)

        """Se anche uno solo non funziona non devono essere aggiunti nessuno"""
        c, d, f = Mock(), Mock(), Mock()
        c.name, f.name = "c", "f"
        del d.name
        self.assertRaises(TypeError, e._register_components, c, d, f)

        self.assertNotIn(c, e.components)
        self.assertNotIn(f, e.components)

        c = Mock()
        c.name = "name_uguale"
        e._register_components(c)
        d = Mock()
        d.name = "name_uguale"

        self.assertRaises(ValueError, e._register_components, d)

        c, f = Mock(), Mock()
        """Se anche uno solo non funziona non devono essere aggiunti nessuno"""
        self.assertRaises(ValueError, e._register_components, c, d, f)
        self.assertNotIn(c, e.components)
        self.assertNotIn(f, e.components)

    def test__deregister_component(self):
        """Verificare che il componente venga deregistrato dall'insimeme dei componenti usando
        la property."""
        e = ED("es")
        components = [Mock() for _ in range(4)]
        e._register_components(*components)
        for c in components:
            e._deregister_components(c)
            self.assertNotIn(c, set(e.components))
        self.assertSetEqual(set(), set(e.components))
        components = [Mock() for _ in range(4)]
        e._register_components(*components)
        e._deregister_components(*components)
        self.assertSetEqual(set(), set(e.components))
        self.assertRaises(KeyError, e._deregister_components, Mock())

    def test_get_component(self):
        e = ED("MyName")
        c, d, f = Mock(), Mock(), Mock()
        c.name, d.name, f.name = "c", "d", "f"
        e._register_components(c, d, f)
        self.assertIs(c, e.get_component("c"))
        self.assertIs(d, e.get_component("d"))
        self.assertIs(f, e.get_component("f"))

        self.assertRaises(KeyError, e.get_component, "prova")

    def test_add_sensor(self):
        ed = ED("MyName")
        si = ed.add_sensor("volume")  # return sensor info
        self.assertIsNotNone(si)
        cc = ed.components
        self.assertEqual(1, len(cc))
        ci = ed.get_component_info("volume")
        self.assertIs(ci, si)

    def test_add_command(self):
        ed = ED("MyName")
        cmd_i = ed.add_command("beep")  # return command info
        self.assertIsNotNone(cmd_i)
        cc = ed.components
        self.assertEqual(1, len(cc))
        ci = ed.get_component_info("beep")
        self.assertIs(ci, cmd_i)
        with patch.object(ed, "_create_and_register", autospec=True) as mock_cr:
            ed.add_command("dd", ("ss", 3), "wwww", hh="ww")
            mock_cr.assert_called_with(CommandFactory, name="dd", default=("ss", 3), description="wwww", hh="ww")

    def test_add_hat(self):
        ed = ED("MyName")
        hat_i = ed.add_hat("alarm")  # return command info
        self.assertIsNotNone(hat_i)
        cc = ed.components
        self.assertEqual(1, len(cc))
        hi = ed.get_component_info("alarm")
        self.assertIs(hi, hat_i)
        with patch.object(ed, "_create_and_register", autospec=True) as mock_cr:
            ed.add_hat("dd", "wwww", hh="ww")
            mock_cr.assert_called_with(HatFactory, name="dd", description="wwww", hh="ww")

    def test_add_requester(self):
        ed = ED("MyName")
        ri = ed.add_requester("request")  # return requester info
        self.assertIsNotNone(ri)
        cc = ed.components
        self.assertEqual(1, len(cc))
        ci = ed.get_component_info("request")
        self.assertIs(ci, ri)

    def test_add_reporter(self):
        ed = ED("MyName")
        r = ed.add_reporter(name="reporter", description="%m.names age",
                            names=["Mark", "Alexander"])  # return reporter info
        self.assertIsNotNone(r)
        cc = ed.components
        self.assertEqual(1, len(cc))
        ci = ed.get_component_info("reporter")
        self.assertIs(ci, r)


class TestExtensionBase(unittest.TestCase):
    """Test the extension base object.
    """

    def setUp(self):
        """Clean all registered descriptions and extension"""
        ES._unregister_all()
        ED._unregister_all()

    def test_base(self):
        """Constructor need a ExtensionDefinition and name"""
        ed = ED("def")
        ed.add_sensor("s0")
        ed.add_sensor("s1")
        ed.add_command("c0")
        ed.add_command("c1")
        self.assertRaises(TypeError, EBS)
        self.assertRaises(TypeError, EBS, ed)
        e = EBS(ed, "goofy")
        self.assertIsNotNone(e)
        self.assertEqual("goofy", e.name)
        self.assertSetEqual({"s0", "s1", "c0", "c1"}, set(e.extension.components_name))

    def assertEqualComponents(self, ex, *components):
        cmps = set()
        for c in components:
            try:
                cmps.add(tuple(c.definition + [c.get()]))
            except AttributeError:
                cmps.add(tuple(c))
        self.assertSetEqual({tuple(c.definition + [c.get()]) for c in ex.components}, cmps)

    def test_do_init_components(self):
        ed = ED("def")
        e = EBS(ed, "MyName")

        self.assertEqual(set(), set(e.extension.components))

        ed.add_sensor("sensor A", 12, "A")
        e = EBS(ed, "MyName2")

        self.assertEqualComponents(e.extension, ["r", "A", "sensor A", 12])

        ed.add_sensor("sensor B", 22, "B")
        e = EBS(ed, "MyName3")
        self.assertEqualComponents(e.extension, ["r", "A", "sensor A", 12],
                                   ["r", "B", "sensor B", 22])


class TestExtension(unittest.TestCase):
    """Test the extension service object.
    """

    def setUp(self):
        """Clean all registered extension and definitions"""
        ES._unregister_all()
        ED._unregister_all()

    @patch("scratch.extension.Extension._init_components")
    def test_base(self, mock_init_components):
        e = E()
        self.assertIsNotNone(e)
        mock_init_components.assert_called_with()

    def test_define_factory(self):
        e = E()
        self.assertIsNone(e.factory)
        factory = Mock()
        e.define_factory(factory)
        self.assertIs(e.factory, factory)

        self.assertRaises(RuntimeError, e.define_factory, Mock())

        """But not if it the same"""
        e.define_factory(factory)

    def test__init_components(self):
        class Ex(E):
            tst_cmp = []

            def do_init_components(self):
                return self.tst_cmp

        e = Ex()

        e._init_components()
        self.assertEqual(set(), set(e.components))

        Ex.tst_cmp = [Mock() for _ in range(3)]
        e._init_components()
        self.assertEqual(set(e.components), set(Ex.tst_cmp))


    def test_components(self):
        """The set of the components"""
        e = E()
        self.assertEqual(set(), set(e.components))
        cmps = {"a": Mock(), "b": Mock()}
        e._components = cmps
        self.assertEqual(set(cmps.values()), set(e.components))


    def test_components_name(self):
        """The set of the components"""
        e = E()
        components = e.components_name
        self.assertSetEqual(set(), set(e.components_name))
        cmps = {"a": Mock(), "b": Mock()}
        e._components = cmps
        self.assertEqual(set(cmps.keys()), set(e.components_name))

    def test_block_specs_empty(self):
        e = E()
        self.assertListEqual([], e.block_specs)

    @patch("scratch.components.Sensor.definition", new_callable=PropertyMock)
    def test_block_specs_more_components(self, m_sensor_definition):
        ed = ED("def")
        ed.add_sensor("test1")
        e = EB(ed)
        definitions = [Mock()]
        m_sensor_definition.side_effect = definitions
        self.assertListEqual(definitions, e.block_specs)

        ed = ED("def2")
        for i in range(5):
            ed.add_sensor("test{}".format(i))
        e = EB(ed)
        definitions = [Mock() for _ in range(5)]
        m_sensor_definition.side_effect = definitions
        self.assertListEqual(definitions, e.block_specs)

    def test_menus_empty(self):
        e = E()
        self.assertDictEqual({}, e.menus)

    def test_menus_some_menus(self):
        ed = ED("def")
        ed.add_reporter("reporter 1", description="%m.first , %d.editable %m.last", first=["1", "2", "3"],
                        editable=[11, 22, 33], last=["pen", "rubber", "rules"])
        e = EB(ed)
        self.assertDictEqual({"first": ["1", "2", "3"], "editable": [11, 22, 33],
                              "last": ["pen", "rubber", "rules"]}, e.menus)
        ed.add_reporter("reporter 2", description="%m.other", other=["a", "b", "c"])
        e = EB(ed)
        self.assertDictEqual({"first": ["1", "2", "3"], "editable": [11, 22, 33],
                              "last": ["pen", "rubber", "rules"], "other": ["a", "b", "c"]}, e.menus)
        "Sanity check"
        ed.add_sensor("sensor")
        e = EB(ed)
        self.assertDictEqual({"first": ["1", "2", "3"], "editable": [11, 22, 33],
                              "last": ["pen", "rubber", "rules"], "other": ["a", "b", "c"]}, e.menus)

    def test_menus_some_menus_no_default_val_no_maps(self):
        ed = ED("def")
        ed.add_reporter("reporter 1", value={None:0}, description="%m.first", first=["1", "2", "3"])
        e = EB(ed)
        self.assertDictEqual({"first": ["1", "2", "3"]}, e.menus)

        ed = ED("def2")
        ed.add_reporter("reporter 1", description="%m.first", first={"1":1, "2":2, "3":3})
        e = EB(ed)
        self.assertDictEqual({"first": ["1", "2", "3"]}, e.menus)

    def test_poll(self):
        ed = ED("def")
        e = EB(ed)
        self.assertDictEqual({}, e.poll())

        ed.add_sensor("s0", value="S")
        e = EB(ed)
        self.assertDictEqual({("s0",): "S"}, e.poll())

        ed.add_sensor("s1", value=1)
        e = EB(ed)
        self.assertDictEqual({("s0",): "S", ("s1",): 1}, e.poll())

        ed.add_reporter("r0", value=1)
        e = EB(ed)
        self.assertDictEqual({("s0",): "S", ("s1",): 1, ("r0",): 1}, e.poll())

        ed.add_reporter("r1", value={None: "female", "Jhon": "male"}, description="Get %m.names gender",
                        names=["Jhon", "Lucy", "Lisa"])
        e = EB(ed)
        self.assertDictEqual({("s0",): "S", ("s1",): 1, ("r0",): 1, ("r1", "Jhon"): "male", ("r1", "Lucy"): "female",
                              ("r1", "Lisa"): "female"}, e.poll())

        """SAnity chack"""
        """hat, command and waitercommand ... no contribution """
        h = ed.add_hat("x0")
        c = ed.add_command("x1")
        w = ed.add_waiter_command("x2")
        ed.add_requester("R0", value=12)
        ed.add_requester("R1", value="AA")
        e = EB(ed)
        self.assertDictEqual({("s0",): "S", ("s1",): 1, ("r0",): 1, ("r1", "Jhon"): "male", ("r1", "Lucy"): "female",
                              ("r1", "Lisa"): "female"}, e.poll())

    def test_busy(self):
        """Return the busy set of all components"""
        ed = ED("def")
        ed.add_sensor("s", value="S")  # empty
        ed.add_sensor("x", value="X")  # empty
        ed.add_hat("h")  # empty
        ed.add_command("hh")  # empty
        ed.add_waiter_command("w")
        ed.add_waiter_command("ww")
        e = EB(ed)
        # empty
        self.assertSetEqual(set(), e.busy)
        """Mock Block.busy .> just waiter command call it"""
        with patch("scratch.components.WaiterCommand.busy", new_callable=PropertyMock) as mock_busy:
            mock_busy.side_effect = [{123, 456}, {1, 2, 3, 4, 456}]
            self.assertSetEqual({123, 456, 1, 2, 3, 4}, e.busy)

    def test_results(self):
        """Returns a tuple of results list a problems"""
        ed = ED("def")

        e = EB(ed)
        self.assertEqual([], e.results)

        ed.add_requester("R0", value=12)
        ed.add_requester("R1", value="AA")
        e = EB(ed)

        self.assertEqual([], e.results)

        r0, r1 = e.get_component("R0"), e.get_component("R1")
        r0.get_async(123)
        r0.get_async(321)
        r1.get_async(23)
        r1.get_async(21)
        r0.set("a")
        r1.set("b")
        res = e.results
        self.assertSetEqual({(123, "a"), (321, "a"), (23, "b"), (21, "b")}, set(res))
        """Catch problems"""

        def do_read():
            raise Exception("problem")

        r0.do_read = do_read
        r0.get_async(333)
        time.sleep(0.01)
        self.assertEqual([(333, "invalid")], e.results)
        self.assertEqual("[R0] : problem", e.problem)

        """SAnity chack"""
        """hat, command and waitercommand ... no contribution """
        ed.add_sensor("s0", value="S")
        ed.add_sensor("s1", value=1)
        ed.add_hat("x0")
        ed.add_command("x1")
        ed.add_waiter_command("x2")
        e = EB(ed)
        self.assertDictEqual({("s0",): "S", ("s1",): 1}, e.poll())
        e.results


@patch("scratch.extension.Extension.components", new_callable=PropertyMock)
@patch("scratch.extension.Extension.do_reset", autospec=True)
def test_reset(self, mock_do_reset, mock_components):
    """Must call reset() for each component, do_reset() (method designed to
    override)"""
    e = E()
    components = [Mock() for _ in range(5)]
    mock_components.return_value = components
    e.reset()
    for m in components:
        m.reset.assert_called_with()
    mock_do_reset.assert_called_with(e)


class TestExtensionService(unittest.TestCase):
    """Test the extension service object.
    """

    def setUp(self):
        """Clean all registered extension services and definitions"""
        ES._unregister_all()
        ED._unregister_all()

    @patch("scratch.extension._BaseHttpMultithreadServer")
    def test_base(self, mock_httpserver):
        """Costructor need just name"""
        self.assertRaises(TypeError, ES)

        es = ES(E(), "goofy")
        self.assertIsNotNone(es)
        self.assertEqual("goofy", es.name)
        mock_httpserver.assert_called_with((EXTENSION_DEFAULT_ADDRESS, EXTENSION_DEFAULT_PORT),
                                           ES.HTTPHandler)
        """Nominal arguments"""
        es = ES(E(), port=31223, address="1.2.3.4", name="donald duck")
        self.assertEqual("donald duck", es.name)
        mock_httpserver.assert_called_with(("1.2.3.4", 31223), ES.HTTPHandler)

    def test_http_conf(self):
        s = scratch.extension._BaseHttpMultithreadServer(("127.0.0.1", 33445),
                                                         ES.HTTPHandler)
        self.assertIsInstance(s, socketserver.ThreadingMixIn)
        self.assertIsInstance(s, http.server.HTTPServer)
        self.assertTrue(s.daemon_threads)
        self.assertTrue(s.allow_reuse_address)


    def test_name(self):
        """Must be unique"""
        es = ES(E(), "goofy")
        self.assertRaises(ValueError, ES, E(), "goofy")

    def test_registered(self):
        ES(E(), "goofy")
        ES(E(), "donald duck")
        self.assertSetEqual({"goofy", "donald duck"}, ES.registered())

    def test_get_registered(self):
        es = ES(E(), "goofy")
        ess = ES(E(), "donald duck")
        self.assertIs(es, ES.get_registered("goofy"))
        self.assertIs(ess, ES.get_registered("donald duck"))
        self.assertRaises(KeyError, ES.get_registered, "minnie")

    @patch("scratch.extension.Extension.menus", new_callable=PropertyMock)
    @patch("scratch.extension.Extension.block_specs", new_callable=PropertyMock)
    def test_description(self, m_extension_block_specs, m_extension_menus):
        es = ES(E(), "MyName")
        block_specs = []
        menus = {}
        res = {"extensionName": "MyName",
               "extensionPort": es.port,
               "blockSpecs": [],
               "menus": menus,
        }
        m_extension_block_specs.return_value = block_specs
        m_extension_menus.return_value = menus
        self.assertDictEqual(res, es.description)
        block_specs = [Mock(), Mock()]
        menus = {Mock(): Mock()}
        res["blockSpecs"] = block_specs
        res["menus"] = menus
        m_extension_block_specs.return_value = block_specs
        m_extension_menus.return_value = menus
        self.assertDictEqual(res, es.description)

    def test_addr_port_proxy(self):
        es = ES(E(), "MyName")
        es._http.server_name = Mock()
        es._http.server_port = Mock()
        self.assertIs(es.address, es._http.server_name)
        self.assertIs(es.port, es._http.server_port)

    def test_render_args(self):
        """Get args and return quoted url"""
        self.assertEqual("a", render_args("a"))
        self.assertEqual("a/b%20c/2/true/false",
                         render_args("a", "b c", 2, True, False))

    def test_poll_dict_render(self):
        """Simple: just one"""
        self.assertEqual("a 1\n", ES.poll_dict_render({("a",): 1}))
        self.assertEqual("a my%20beautiful%20phrase\n", ES.poll_dict_render({("a",): "my beautiful phrase"}))

        self.assertEqual("a/b%20c/true my%20beautiful%20phrase\n",
                         ES.poll_dict_render({("a", "b c", True): "my beautiful phrase"}))

        self.assertSetEqual({"a 1", "a/a%20b cc", "c/true dd"}, set(ES.poll_dict_render(
            {("a",): 1, ("a", "a b"): "cc", ("c", True): "dd"})[:-1].split("\n")))

    def test_busy_render(self):
        self.assertEqual("", ES.busy_render(set()))
        busy = {1, 2, 3, 4}
        r = ES.busy_render(busy)
        self.assertEquals("_busy ", r[:len("_busy ")])
        self.assertEquals("\n", r[-1])
        self.assertSetEqual(busy, {int(e) for e in r[len("_busy "):].split(" ")})

    def test_results_render(self):
        self.assertEqual("", ES.results_render(set()))
        r = ES.results_render({(1232, 2), (3423, "sss"), (21, "invalid")})
        self.assertEquals("\n", r[-1])
        self.assertSetEqual({"_result 1232 2", "_result 3423 sss", "_result 21 invalid"},
                            set(r[:-1].split("\n")))


    def test_problems_render(self):
        es = ES(E(), "MyName")
        self.assertEqual("", es.problem_render(""))
        self.assertEqual("_problem My Problem\n", es.problem_render("My Problem"))

    @patch("scratch.extension.Extension.problem", new_callable=PropertyMock)
    @patch("scratch.extension.ExtensionService.problem_render", return_value="problem_render\n")
    @patch("scratch.extension.Extension.results", new_callable=PropertyMock)
    @patch("scratch.extension.ExtensionService.results_render", return_value="results_render\n")
    @patch("scratch.extension.Extension.busy", new_callable=PropertyMock)
    @patch("scratch.extension.ExtensionService.busy_render", return_value="busy_render\n")
    @patch("scratch.extension.Extension.poll")
    @patch("scratch.extension.ExtensionService.poll_dict_render", return_value="dict_render\n")
    def test__poll_cgi(self, mock_poll_dict_render, mock_poll, mock_busy_render, mock_busy,
                       mock_results_render, mock_results, mock_problem_render, mock_problem):
        es = ES(E(), "MyName")
        self.assertEqual(es._poll_cgi(Mock(autospec=ES.HTTPHandler)), mock_poll_dict_render.return_value +
                         mock_busy_render.return_value + mock_results_render.return_value +
                         mock_problem_render.return_value)
        self.assertTrue(mock_poll.called)
        mock_poll_dict_render.assert_called_with(mock_poll.return_value)
        self.assertTrue(mock_busy.called)
        mock_busy_render.assert_called_with(mock_busy.return_value)
        self.assertTrue(mock_busy.called)
        mock_busy_render.assert_called_with(mock_busy.return_value)
        mock_results_render.assert_called_with(mock_results.return_value)
        self.assertTrue(mock_results.called)
        mock_results_render.assert_called_with(mock_results.return_value)
        mock_problem_render.assert_called_with(mock_problem.return_value)
        self.assertTrue(mock_problem.called)
        mock_problem_render.assert_called_with(mock_problem.return_value)

    @patch("threading.Thread", autospec=True)
    def test_start(self, mock_thread):
        es = ES(E(), "MyName")
        """Check if the costructor set _server_thread to None"""
        self.assertIsNone(es._server_thread)
        mock_server_thread = mock_thread.return_value
        es.start()
        mock_thread.assert_called_with(name="MyName HTTP Server", target=es._http.serve_forever)
        self.assertIs(es._server_thread, mock_server_thread)
        self.assertTrue(mock_server_thread.daemon)
        self.assertTrue(mock_server_thread.start.called)

        mock_thread.reset_mock()
        es.start()
        self.assertFalse(mock_thread.called)
        self.assertFalse(mock_server_thread.start.called)

    @patch("threading.Thread.join", autospec=True)
    @patch("scratch.extension.HTTPServer.shutdown", autospec=True)
    def test_stop(self, mock_shutdown, mock_join):
        es = ES(E(), "MyName")
        self.assertIsNone(es._server_thread)
        """Do nothing .... but not exception"""
        es.stop()
        self.assertFalse(mock_shutdown.called)
        self.assertFalse(mock_join.called)
        es.start()
        self.assertIsNotNone(es._server_thread)
        es.stop()
        self.assertTrue(mock_shutdown.called)
        self.assertTrue(mock_join.called)
        self.assertIsNone(es._server_thread)

        """Do nothing .... but not exception"""
        es.stop()

    def test_running(self):
        es = ES(E(), "MyName")
        self.assertFalse(es.running)
        es.start()
        self.assertTrue(es.running)
        es.start()
        self.assertTrue(es.running)
        es.stop()
        self.assertFalse(es.running)
        es.stop()
        self.assertFalse(es.running)
        try:
            es.running = True
            self.fail("MUST be a readonly property")
        except AttributeError:
            pass

    def test_reset(self):
        """Must call reset() for each component, do_reset() (method designed to
        override and return "" """

        class Ex(E):
            reset_call = False

            def reset(self):
                Ex.reset_call = True

        es = ES(Ex(), "MyName")
        self.assertFalse(Ex.reset_call)
        self.assertEqual("", es.reset(Mock()))
        self.assertTrue(Ex.reset_call)

    @patch("scratch.extension.ExtensionService._resolve_components_cgi", autospec=True)
    @patch("scratch.extension.ExtensionService._resolve_local_cgi", autospec=True)
    def test__get_cgi(self, mock_resolve_local_cgi, mock_resolve_components_cgi):
        """Resolve order:
        - ask to component : _resolve_components_cgi()
        - looking for local cgi : _resolve_local_cgi()
        """
        es = ES(E(), "MyName")
        self.assertIs(mock_resolve_components_cgi.return_value, es._get_cgi("my_path"))
        self.assertFalse(mock_resolve_local_cgi.called)
        mock_resolve_components_cgi.reset_mock

        mock_resolve_components_cgi.return_value = None
        self.assertIs(mock_resolve_local_cgi.return_value, es._get_cgi("my_path"))
        self.assertTrue(mock_resolve_components_cgi.called)

    @patch("scratch.extension.Extension.components", new_callable=PropertyMock)
    def test__resolve_components_cgi(self, mock_components):
        es = ES(E(), "MyName")
        components = [Mock() for _ in range(5)]
        mock_components.return_value = components
        for m in components[:-1]:
            m.get_cgi.return_value = None
        self.assertIs(components[-1].get_cgi.return_value, es._resolve_components_cgi("path"))
        for m in components:
            m.get_cgi.assert_called_wirth("path")
        components[0].get_cgi.return_value = 11
        self.assertEqual(11, es._resolve_components_cgi("path"))


@patch("scratch.extension.BaseHTTPRequestHandler.command", create=True, new_callable=PropertyMock)
@patch("scratch.extension.BaseHTTPRequestHandler.path", create=True, new_callable=PropertyMock)
@patch("scratch.extension.BaseHTTPRequestHandler.request_version", create=True, new_callable=PropertyMock)
@patch("scratch.extension.ExtensionService.HTTPHandler.end_headers")
@patch("scratch.extension.ExtensionService.HTTPHandler.send_header")
@patch("scratch.extension.ExtensionService.HTTPHandler.send_response")
@patch("scratch.extension.ExtensionService.HTTPHandler.log_request")
@patch("scratch.extension.ExtensionService.HTTPHandler.parse_request", return_value=True)
class TestExtension_HTTPHandler(unittest.TestCase):
    """We will test http request to extension handler"""

    def setUp(self):
        """Clean all registered descriptions"""
        ES._unregister_all()
        self.es = ES(E(), "MyName")
        self.mock_request = MagicMock()
        self.mock_client_address = ("1.2.3.4", 34234)
        self.mock_wfile = self.mock_request.makefile.return_value

    def do_request(self):
        handler = ES.HTTPHandler(self.mock_request, self.mock_client_address, self.es._http)

    @patch("scratch.extension.ExtensionService._poll_cgi", return_value="POLLER")
    def test_handle_poll(self, mock_cgi, mock_parse_request, mock_log_request,
                         mock_send_response, mock_send_header, mock_end_headers,
                         mock_request_version,
                         mock_path, mock_command):
        mock_path.return_value = "/poll"
        mock_command.return_value = "GET"
        self.do_request()
        self.assertTrue(mock_cgi.called)
        mock_send_response.assert_called_with(200)
        self.mock_wfile.write.assert_called_with(bytes(mock_cgi.return_value, "utf-8"))
        mock_send_header.assert_called_with("Content-type", "text/html")
        self.assertTrue(mock_end_headers.called)

        mock_send_response.reset_mock()
        mock_send_header.reset_mock()
        mock_end_headers.reset_mock()
        mock_command.return_value = "HEAD"
        self.do_request()
        mock_send_response.assert_called_with(200)
        mock_send_header.assert_called_with("Content-type", "text/html")
        self.assertTrue(mock_end_headers.called)


    def test_handle_not_exist(self, mock_parse_request, mock_log_request,
                              mock_send_response, mock_send_header, mock_end_headers,
                              mock_request_version,
                              mock_path, mock_command):
        mock_path.return_value = "/poroppopero"
        mock_command.return_value = "GET"
        self.do_request()
        mock_send_response.assert_called_with(404)
        self.assertTrue(mock_end_headers.called)

        mock_send_response.reset_mock()
        mock_send_header.reset_mock()
        mock_end_headers.reset_mock()
        mock_command.return_value = "HEAD"
        self.do_request()
        mock_send_response.assert_called_with(404)
        self.assertTrue(mock_end_headers.called)

    def test_handle_crossdomain_xml(self, mock_parse_request, mock_log_request,
                                    mock_send_response, mock_send_header, mock_end_headers,
                                    mock_request_version,
                                    mock_path, mock_command):
        mock_path.return_value = "/crossdomain.xml"
        mock_command.return_value = "GET"
        self.do_request()
        mock_send_response.assert_called_with(200)
        data = """<cross-domain-policy>
<allow-access-from domain="*" to-ports="{}"/>
</cross-domain-policy>""".format(self.es.port)
        self.mock_wfile.write.assert_called_with(bytes(data, "utf-8"))
        mock_send_header.assert_called_with("Content-type", "text/xml")
        self.assertTrue(mock_end_headers.called)

        mock_send_response.reset_mock()
        mock_send_header.reset_mock()
        mock_end_headers.reset_mock()
        mock_command.return_value = "HEAD"
        self.do_request()
        mock_send_response.assert_called_with(200)
        mock_send_header.assert_called_with("Content-type", "text/xml")
        self.assertTrue(mock_end_headers.called)

    @patch("scratch.extension.ExtensionService.reset", return_value="")
    def test_handle_reset_all_xml(self, mock_reset, mock_parse_request, mock_log_request,
                                  mock_send_response, mock_send_header, mock_end_headers,
                                  mock_request_version,
                                  mock_path, mock_command):
        """Must respond by a empty page and call reset() exstension method"""

        mock_path.return_value = "/reset_all"
        mock_command.return_value = "GET"
        self.do_request()
        mock_send_response.assert_called_with(200)
        mock_reset.asset_called_with(self.mock_request)
        data = ""
        self.mock_wfile.write.assert_called_with(bytes(data, "utf-8"))
        mock_send_header.assert_called_with("Content-type", "text/html")
        self.assertTrue(mock_end_headers.called)

        mock_send_response.reset_mock()
        mock_send_header.reset_mock()
        mock_end_headers.reset_mock()
        mock_reset.reset_mock()
        mock_command.return_value = "HEAD"
        self.do_request()
        self.assertFalse(mock_reset.called)
        mock_send_response.assert_called_with(200)
        mock_send_header.assert_called_with("Content-type", "text/html")
        self.assertTrue(mock_end_headers.called)


if __name__ == '__main__':
    unittest.main()
