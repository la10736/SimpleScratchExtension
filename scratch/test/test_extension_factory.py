__author__ = 'michele'

import unittest
from scratch.portability.mock import Mock
from scratch.extension import ExtensionServiceFactory as EF


class TestExtensionFactory(unittest.TestCase):
    """We will test the factory object. The factory object are "immutable" and
    not expose any methods to change how do the work. Moreover a factory contain a
    dictionary of his created extension services.
    """

    def setUp(self):
        EF.deregister_all()

    def tearDown(self):
        EF.deregister_all()

    def test_base(self):
        ef = EF()
        self.assertIsNotNone(ef)
        self.assertEqual("anonymous", ef.name)
        ef = EF("PPP")
        self.assertEqual("PPP", ef.name)
        ef = EF(name="QQQ")
        self.assertEqual("QQQ", ef.name)

        self.assertSetEqual(set(), ef.extensions)

    def test_named_factory_can_not_be_duplicated(self):
        ef = EF("PPP")
        self.assertRaises(ValueError, EF, "PPP")

    def test_anonymous_factory_are_not_limitaed(self):
        efs = [EF() for _ in range(4)]
        self.assertEqual([e.name for e in efs], ["anonymous"] * 4)

    def test_get_registered_factory(self):
        ef = EF("PPP")
        self.assertIs(ef, EF.registered("PPP"))
        """It will not dead"""
        i = id(ef)
        del ef
        self.assertEqual(i, id(EF.registered("PPP")))
        ef = EF("QQQ")
        """None or no argument return the set of the names"""
        self.assertEqual({"PPP", "QQQ"}, EF.registered())
        self.assertEqual({"PPP", "QQQ"}, EF.registered(None))
        self.assertEqual({"PPP", "QQQ"}, EF.registered(name=None))

        class trace(EF):
            DEAD = False

            def __del__(self):
                trace.DEAD = True

        ef = trace()
        self.assertIsNone(EF.registered("anonymous"))
        """ It will dead"""
        del ef
        self.assertTrue(trace.DEAD)


    def test_deregistered_factory(self):
        class trace(EF):
            DEAD = False

            def __del__(self):
                trace.DEAD = True

        ef = trace("PPP")
        self.assertIs(ef, EF.registered("PPP"))
        EF.deregister("PPP")
        self.assertIsNone(EF.registered("PPP"))
        del ef
        self.assertTrue(trace.DEAD)

        """Exception if not exist"""
        self.assertRaises(KeyError, EF.deregister, "PPP")

    def test_create(self):
        """The base implementation of do_create() is abstract and raise a NotImplementedError"""
        ef = EF("PPP")
        self.assertRaises(NotImplementedError, ef.create)
        extensions_base = [Mock() for _ in range(3)]
        extensions = extensions_base[:]

        def do_create(*args, **kwargs):
            return extensions

        ef.do_create = do_create
        self.assertEqual(set(extensions), set(ef.create()))
        self.assertSetEqual(set(extensions), ef.extensions)
        for e in extensions:
            e.define_factory.assert_called_with(ef)

    def test_port_generator(self):
        ef = EF("pp")
        k = 100
        for i in ef.port_generator(k):
            self.assertEqual(k, i)
            k += 1
            if k > 105:
                break
        self.assertEqual([10, 20, 30], [i for i in ef.port_generator([10, 20, 30])])

    def test_port_generator_0_always_0(self):
        ef = EF("pp")
        i = 0
        for p in ef.port_generator(0):
            self.assertEqual(0, p)
            i += 1
            if i > 200:
                break
        self.assertGreater(i, 200)
        self.assertEqual(0, p)


if __name__ == '__main__':
    unittest.main()
