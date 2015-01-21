
__author__ = 'michele'
import unittest
from scratch.portability.mock import patch, Mock, PropertyMock, MagicMock
from scratch.extension import ExtensionDefinition as ED
from scratch.extension import Extension as E, EXTENSION_DEFAULT_PORT, EXTENSION_DEFAULT_ADDRESS
from scratch.extension import ExtensionBase as EB, EXTENSION_DEFAULT_PORT, EXTENSION_DEFAULT_ADDRESS
from scratch.components import CommandFactory, Sensor


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
        self.assertRaises(TypeError, E)
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


class TestExtensionBase(unittest.TestCase):
    """Test the extension base object.
    """

    def setUp(self):
        """Clean all registered descriptions and extension"""
        E._unregister_all()
        ED._unregister_all()

    def test_base(self):
        """Constructor need a ExtensionDefinition and name"""
        ed = ED("def")
        ed.add_sensor("s0")
        ed.add_sensor("s1")
        ed.add_command("c0")
        ed.add_command("c1")
        self.assertRaises(TypeError, EB)
        self.assertRaises(TypeError, EB, ed)
        e = EB(ed, "goofy")
        self.assertIsNotNone(e)
        self.assertEqual("goofy", e.name)
        self.assertSetEqual({"s0","s1","c0","c1"}, set(e.components_name))

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
        e = EB(ed, "MyName")

        self.assertEqual(set(), set(e.components))

        ed.add_sensor("sensor A", 12, "A")
        e = EB(ed, "MyName2")

        self.assertEqualComponents(e, ["r", "A", "sensor A", 12])

        ed.add_sensor("sensor B", 22, "B")
        e = EB(ed, "MyName3")
        self.assertEqualComponents(e, ["r", "A", "sensor A", 12],
                                   ["r", "B", "sensor B", 22])

class TestExtension(unittest.TestCase):
    """Test the extension object.
    """

    def setUp(self):
        """Clean all registered extension and definitions"""
        E._unregister_all()
        ED._unregister_all()

    @patch("scratch.extension.HTTPServer")
    @patch("scratch.extension.Extension._init_components")
    def test_base(self, mock_init_components, mock_httpserver):
        """Costructor need just name"""
        self.assertRaises(TypeError, E)

        e = E("goofy")
        self.assertIsNotNone(e)
        self.assertEqual("goofy", e.name)
        mock_init_components.assert_called_with()
        mock_httpserver.assert_called_with((EXTENSION_DEFAULT_ADDRESS, EXTENSION_DEFAULT_PORT),
                                           E.HTTPHandler)
        """Nominal arguments"""
        e = E(port=31223, address="1.2.3.4", name="donald duck")
        self.assertEqual("donald duck", e.name)
        mock_httpserver.assert_called_with(("1.2.3.4", 31223), E.HTTPHandler)

    def test_name(self):
        """Must be unique"""
        e = E("goofy")
        self.assertRaises(ValueError, E, "goofy")

    def test_registered(self):
        E("goofy")
        E("donald duck")
        self.assertSetEqual({"goofy", "donald duck"}, E.registered())

    def test_get_registered(self):
        e = E("goofy")
        ee = E("donald duck")
        self.assertIs(e, E.get_registered("goofy"))
        self.assertIs(ee, E.get_registered("donald duck"))
        self.assertRaises(KeyError, E.get_registered, "minnie")

    def test_define_factory(self):
        e = E("MyName")
        self.assertIsNone(e.factory)
        factory = Mock()
        e.define_factory(factory)
        self.assertIs(e.factory, factory)

        self.assertRaises(RuntimeError, e.define_factory, Mock())

        """But not if it the same"""
        e.define_factory(factory)

    def test_define_group(self):
        e = E("MyName")
        self.assertIsNone(e.group)
        group = Mock()
        e.define_group(group)
        self.assertIs(e.group, group)

        self.assertRaises(RuntimeError, e.define_group, Mock())

        """But not if it the same"""
        e.define_group(group)

    def test__init_components(self):
        class Ex(E):
            tst_cmp = []
            def do_init_components(self):
                return self.tst_cmp
        e = Ex("goofy")

        e._init_components()
        self.assertEqual(set(), set(e.components))

        Ex.tst_cmp = [Mock() for _ in range(3)]
        e._init_components()
        self.assertEqual(set(e.components), set(Ex.tst_cmp))


    def test_components(self):
        """The set of the components"""
        e = E("es")
        components = e.components
        self.assertEqual(set(), set(components))


    def test_components_name(self):
        """The set of the components"""
        e = E("es")
        components = e.components
        self.assertSetEqual(set(), set(components))

    def assertEqualDescription(self, a, b):
        a, b = a.copy(), b.copy()
        a["blockSpecs"] = set(a["blockSpecs"])
        b["blockSpecs"] = set(b["blockSpecs"])
        self.assertDictEqual(a, b)

    @patch("scratch.components.Sensor.definition", new_callable=PropertyMock)
    def test_description_empty(self, m_sensor_definition):
        e = E("MyName")
        res = {"extensionName": "MyName",
               "extensionPort": e.port,
               "blockSpecs": []
        }
        self.assertEqualDescription(res, e.description)

    @patch("scratch.components.Sensor.definition", new_callable=PropertyMock)
    def test_description_one_component(self, m_sensor_definition):
        ed = ED("def")
        ed.add_sensor("test1")
        e = EB(ed, "MyName")
        definitions = [Mock()]
        res = {"extensionName": "MyName",
               "extensionPort": e.port,
               "blockSpecs": definitions
        }
        m_sensor_definition.side_effect = definitions
        self.assertEqualDescription(res, e.description)

    @patch("scratch.components.Sensor.definition", new_callable=PropertyMock)
    def test_description_more_components(self, m_sensor_definition):
        ed = ED("def")
        for i in range(5):
            ed.add_sensor("test%d" % i)
        e = EB(ed, "MyName")
        definitions = [Mock() for _ in range(5)]
        res = {"extensionName": "MyName",
               "extensionPort": e.port,
               "blockSpecs": definitions
        }
        m_sensor_definition.side_effect = definitions
        self.assertEqualDescription(res, e.description)

    def test_addr_port_proxy(self):
        e = E("MyName")
        e._http.server_name = Mock()
        e._http.server_port = Mock()
        self.assertIs(e.address, e._http.server_name)
        self.assertIs(e.port, e._http.server_port)

    def test_poll(self):
        ed = ED("def")
        e = EB(ed, "MyName")
        self.assertDictEqual({}, e.poll())

        ed.add_sensor("s", value="S")
        e = EB(ed, "MyName 1")
        self.assertDictEqual({"s": "S"}, e.poll())

        ed.add_sensor("d", value=1)
        e = EB(ed, "MyName 2")
        self.assertDictEqual({"s": "S", "d": 1}, e.poll())

    def test_poll_dict_render(self):
        lines = ["a VV", "c DD", "vujdvj cveo djicvo wcowio"]
        d = dict([s.split(" ", 1) for s in lines])
        self.assertSetEqual(set(E.poll_dict_render(d).split("\n")[:-1]),
                            set(lines))
        self.fail("nome deve essere una stringa o una tupla. il risultato deve essere urlencoded "
                  "per ogni elemento della tupla del nome es uniti con /. Il valore deve essere url"
                  "encoded.")

    @patch("scratch.extension.Extension.poll")
    @patch("scratch.extension.Extension.poll_dict_render")
    def test__poll_cgi(self, mock_poll_dict_render, mock_poll):
        e = E("MyName")
        self.assertIs(e._poll_cgi(Mock(autospec=E.HTTPHandler)), mock_poll_dict_render.return_value)
        self.assertTrue(mock_poll.called)
        mock_poll_dict_render.assert_called_with(mock_poll.return_value)

    @patch("threading.Thread", autospec=True)
    def test_start(self, mock_thread):
        e = E("MyName")
        """Check if the costructor set _server_thread to None"""
        self.assertIsNone(e._server_thread)
        mock_server_thread = mock_thread.return_value
        e.start()
        mock_thread.assert_called_with(name="MyName HTTP Server", target=e._http.serve_forever)
        self.assertIs(e._server_thread, mock_server_thread)
        self.assertTrue(mock_server_thread.daemon)
        self.assertTrue(mock_server_thread.start.called)

        mock_thread.reset_mock()
        e.start()
        self.assertFalse(mock_thread.called)
        self.assertFalse(mock_server_thread.start.called)

    @patch("threading.Thread.join", autospec=True)
    @patch("scratch.extension.HTTPServer.shutdown", autospec=True)
    def test_stop(self, mock_shutdown, mock_join):
        e = E("MyName")
        self.assertIsNone(e._server_thread)
        """Do nothing .... but not exception"""
        e.stop()
        self.assertFalse(mock_shutdown.called)
        self.assertFalse(mock_join.called)
        e.start()
        self.assertIsNotNone(e._server_thread)
        e.stop()
        self.assertTrue(mock_shutdown.called)
        self.assertTrue(mock_join.called)
        self.assertIsNone(e._server_thread)

        """Do nothing .... but not exception"""
        e.stop()

    def test_running(self):
        e = E("MyName")
        self.assertFalse(e.running)
        e.start()
        self.assertTrue(e.running)
        e.start()
        self.assertTrue(e.running)
        e.stop()
        self.assertFalse(e.running)
        e.stop()
        self.assertFalse(e.running)
        try:
            e.running = True
            self.fail("MUST be a readonly property")
        except AttributeError:
            pass

    @patch("scratch.extension.Extension.components", new_callable=PropertyMock)
    @patch("scratch.extension.Extension.do_reset", autospec=True)
    def test_reset(self, mock_do_reset, mock_components):
        """Must call reset() for each component, do_reset() (method designed to
        override and return "" """
        e = E("MyName")
        components = [Mock() for _ in range(5)]
        mock_components.return_value = components
        request = Mock()
        self.assertEqual("", e.reset(request))
        for m in components:
            m.reset.assert_called_with(request)
        mock_do_reset.assert_called_with(e, request)

    @patch("scratch.extension.Extension._resolve_components_cgi", autospec=True)
    @patch("scratch.extension.Extension._resolve_local_cgi", autospec=True)
    def test__get_cgi(self, mock_resolve_local_cgi, mock_resolve_components_cgi):
        """Resolve order:
        - ask to component : _resolve_components_cgi()
        - looking for local cgi : _resolve_local_cgi()
        """
        e = E("MyName")
        self.assertIs(mock_resolve_components_cgi.return_value, e._get_cgi("my_path"))
        self.assertFalse(mock_resolve_local_cgi.called)
        mock_resolve_components_cgi.reset_mock

        mock_resolve_components_cgi.return_value = None
        self.assertIs(mock_resolve_local_cgi.return_value, e._get_cgi("my_path"))
        self.assertTrue(mock_resolve_components_cgi.called)

    @patch("scratch.extension.Extension.components", new_callable=PropertyMock)
    def test__resolve_components_cgi(self, mock_components):
        e = E("MyName")
        components = [Mock() for _ in range(5)]
        mock_components.return_value = components
        for m in components[:-1]:
            m.get_cgi.return_value = None
        self.assertIs(components[-1].get_cgi.return_value, e._resolve_components_cgi("path"))
        for m in components:
            m.get_cgi.assert_called_wirth("path")
        components[0].get_cgi.return_value = 11
        self.assertEqual(11, e._resolve_components_cgi("path"))


@patch("scratch.extension.BaseHTTPRequestHandler.command", create=True, new_callable=PropertyMock)
@patch("scratch.extension.BaseHTTPRequestHandler.path", create=True, new_callable=PropertyMock)
@patch("scratch.extension.BaseHTTPRequestHandler.request_version", create=True, new_callable=PropertyMock)
@patch("scratch.extension.Extension.HTTPHandler.end_headers")
@patch("scratch.extension.Extension.HTTPHandler.send_header")
@patch("scratch.extension.Extension.HTTPHandler.send_response")
@patch("scratch.extension.Extension.HTTPHandler.log_request")
@patch("scratch.extension.Extension.HTTPHandler.parse_request", return_value=True)
class TestExtension_HTTPHandler(unittest.TestCase):
    """We will test http request to extension handler"""

    def setUp(self):
        """Clean all registered descriptions"""
        E._unregister_all()
        self.e = E("MyName")
        self.mock_request = MagicMock()
        self.mock_client_address = ("1.2.3.4", 34234)
        self.mock_wfile = self.mock_request.makefile.return_value

    def do_request(self):
        handler = E.HTTPHandler(self.mock_request, self.mock_client_address, self.e._http)

    @patch("scratch.extension.Extension._poll_cgi", return_value="POLLER")
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
</cross-domain-policy>""".format(self.e.port)
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

    @patch("scratch.extension.Extension.reset", return_value="")
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
