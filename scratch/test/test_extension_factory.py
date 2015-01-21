
__author__ = 'michele'

import unittest
from scratch.portability.mock import Mock
from scratch.extension import ExtensionFactory as EF, ExtensionGroup as EG


class TestExtensionGroup(unittest.TestCase):
    """A set of extension that work in team."""

    def setUp(self):
        EF.deregister_all()

    def tearDown(self):
        EF.deregister_all()

    def test_base(self):
        ef = EF("PPP")
        ex = Mock()
        eg = EG(ef, "Group", ex)
        self.assertSetEqual({ex}, eg.extensions)
        self.assertIs(eg.factory, ef)
        self.assertEqual("Group", eg.name)
        extensions = [Mock(factory=ef) for _ in range(3)]
        eg = EG(ef, "Group", *extensions)
        self.assertSetEqual(set(extensions), eg.extensions)

        for e in extensions:
            e.define_group.assert_called_with(eg)

    def test_start_stop_running(self):
        ef = EF("PPP")
        extensions = [Mock(factory=ef) for _ in range(3)]
        eg = EG(ef, "Group", *extensions)
        eg.start()
        for e in extensions:
            self.assertTrue(e.start.called)
        eg.stop()
        for e in extensions:
            self.assertTrue(e.start.called)
        for e in extensions:
            e.running = True
        self.assertTrue(eg.running)
        extensions[0].running = False
        self.assertFalse(eg.running)
        extensions[0].running = True
        extensions[1].running = False
        self.assertFalse(eg.running)
        extensions[1].running = True
        self.assertTrue(eg.running)


class TestExtensionFactory(unittest.TestCase):
    """We will test the factory object. The factory object are "immutable" because
    do not expose any method to change how do the work. Moreover a factory contain a
    dictionary of his created exstension.
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

    def test_groups(self):
        ef = EF("PPP")
        self.assertEqual(set(), ef.groups)
        self.assertRaises(KeyError, ef.group, "goofy")

    def test_create(self):
        """The base implementation of do_create() is abstract and raise a NotImplementedError"""
        ef = EF("PPP")
        self.assertRaises(NotImplementedError, ef.create)
        extensions_base = [Mock() for _ in range(3)]
        extensions = extensions_base[:]

        def do_create(group_name, *args, **kwargs):
            return extensions

        ef.do_create = do_create
        self.assertEqual(set(extensions), set(ef.create().extensions))
        """Create a group called 1"""
        self.assertEqual({"1"}, ef.groups)
        self.assertSetEqual(set(extensions), ef.extensions)
        self.assertSetEqual(ef.group("1").extensions, ef.extensions)
        self.assertIs(ef.group("1").factory, ef)
        self.assertEqual(ef.group("1").name, "1")
        for e in extensions:
            e.define_factory.assert_called_with(ef)

        """Just one extension no group"""
        extensions = extensions_base[:1]
        self.assertEqual(extensions, ef.create())
        """No other groups"""
        self.assertEqual({"1"}, ef.groups)

        """Just one other group"""
        extensions = extensions_base[:2]
        self.assertEqual(set(extensions), set(ef.create().extensions))
        self.assertEqual({"1","2"}, ef.groups)

        """Named group"""
        extensions = extensions_base[1:]
        self.assertEqual(set(extensions), set(ef.create(group_name="minnie").extensions))
        self.assertEqual({"1","2","minnie"}, ef.groups)

        """Named group on single extension are ignored"""
        extensions = extensions_base[2:]
        self.assertEqual(extensions, ef.create(group_name="goofy"))
        self.assertEqual({"1","2","minnie"}, ef.groups)

        """Already existing groups raise exception both for 1 or more extension"""
        extensions = extensions_base[1:]
        self.assertRaises(ValueError, ef.create, group_name="minnie")
        extensions = extensions_base[2:]
        self.assertRaises(ValueError, ef.create, group_name="minnie")
        self.assertEqual({"1","2","minnie"}, ef.groups)

    def test_extension_port_generator(self):
        ef = EF("pp")
        k = 100
        for i in ef.port_generator(k):
            self.assertEqual(k, i)
            k += 1
            if k > 105:
                break
        self.assertEqual([10,20,30], [i for i in ef.port_generator([10,20,30])])



if __name__ == '__main__':
    unittest.main()
