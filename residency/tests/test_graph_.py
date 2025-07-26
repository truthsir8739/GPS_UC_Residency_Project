import unittest
from residency.graph import Graph

class TestGraph(unittest.TestCase):

    def setUp(self):
        self.graph = Graph()
        self.graph.add_edge('A', 'B', 4, 'high', tip='Blind spot alert: check right', blind_spot=True)
        self.graph.add_edge('A', 'C', 5, 'low', tip='Instructor: maintain speed')  # Changed from 2 to 5
        self.graph.add_edge('B', 'D', 5, 'medium')
        self.graph.add_edge('C', 'B', 1, 'low')
        self.graph.add_edge('C', 'E', 10, 'high')
        self.graph.add_edge('D', 'E', 2, 'low')
        self.graph.add_edge('E', 'F', 3, 'medium')

    def test_learner_mode_path_avoids_blind_spots(self):
        """Learner mode avoids blind spots and collects tips."""
        print("\n[TEST] Learner mode pathfinding from A to F")
        path, tips, blind_alerts = self.graph.dijkstra('A', 'F', learner_mode=True)
        print("→ Path:", path)
        print("→ Tips:", tips)
        print("→ Blind Spots:", blind_alerts)

        with self.subTest("Path avoids blind spots"):
            self.assertEqual(path, ['A', 'C', 'B', 'D', 'E', 'F'])

        with self.subTest("Tip included from safe edge"):
            self.assertIn('Instructor: maintain speed', tips)

        with self.subTest("No blind spot alerts on taken path"):
            self.assertNotIn('Blind spot at A to B', blind_alerts)

    def test_non_learner_mode_includes_blind_spot_edges(self):
        """Normal mode includes blind spot edges without filtering."""
        print("\n[TEST] Non-learner mode includes blind spots")
        path, tips, blind_alerts = self.graph.dijkstra('A', 'F', learner_mode=False)
        print("→ Path:", path)
        print("→ Tips:", tips)
        print("→ Blind Spots:", blind_alerts)

        self.assertIn('A', path)
        self.assertIn('B', path)
        self.assertIn('Blind spot at A to B', blind_alerts)

    def test_disconnected_node_returns_empty_path(self):
        """Path to unreachable node returns empty values."""
        print("\n[TEST] Disconnected node: pathfinding to G")
        path, tips, blind_alerts = self.graph.dijkstra('A', 'G', learner_mode=True)
        print("→ Path:", path)
        print("→ Tips:", tips)
        print("→ Blind Spots:", blind_alerts)

        self.assertEqual(path, [])
        self.assertEqual(tips, [])
        self.assertEqual(blind_alerts, [])

    def test_same_start_and_end_node(self):
        """Same start/end node returns only that node, with no tips or alerts."""
        print("\n[TEST] Same start and end: A to A")
        g = Graph()
        path, tips, blind_alerts = g.dijkstra('A', 'A', learner_mode=True)
        print("→ Path:", path)
        print("→ Tips:", tips)
        print("→ Blind Spots:", blind_alerts)

        self.assertEqual(path, ['A'])
        self.assertEqual(tips, [])
        self.assertEqual(blind_alerts, [])

    def test_learner_mode_falls_back_when_only_path_has_blind_spot(self):
        """If blind spot edge is the only route, it should be taken with alert."""
        print("\n[TEST] Learner mode fallback: only path includes blind spot")
        g = Graph()
        g.add_edge('X', 'Y', 1, 'high', tip='Caution: merge zone', blind_spot=True)
        g.add_edge('Y', 'Z', 1, 'low', tip='Smooth braking')
        
        path, tips, blind_alerts = g.dijkstra('X', 'Z', learner_mode=True)
        print("→ Path:", path)
        print("→ Tips:", tips)
        print("→ Blind Spots:", blind_alerts)

        self.assertEqual(path, ['X', 'Y', 'Z'])
        self.assertIn('Caution: merge zone', tips)
        self.assertIn('Blind spot at X to Y', blind_alerts)

    def test_multiple_equal_paths_choose_lowest_cost(self):
        """When multiple paths exist, the one with lowest total weight is selected."""
        print("\n[TEST] Multiple paths available: shortest preferred")
        g = Graph()
        g.add_edge('A', 'B', 1, 'low')
        g.add_edge('A', 'C', 2, 'low')
        g.add_edge('B', 'D', 1, 'low')
        g.add_edge('C', 'D', 1, 'low')
        path, _, _ = g.dijkstra('A', 'D', learner_mode=True)
        print("→ Path:", path)
        self.assertEqual(path, ['A', 'B', 'D'])  # Lower cost: 1+1 = 2 vs. 2+1 = 3

if __name__ == "__main__":
    unittest.main(verbosity=2)
