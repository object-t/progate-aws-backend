import pytest
import time
from unittest.mock import patch
from routers.costs import calculate_final_cost, find_resource_types


class TestCostPerformance:
    """コスト計算のパフォーマンステスト"""

    def test_large_structure_performance(self):
        """大規模構造でのパフォーマンステスト"""
        # 大規模な構造データを生成
        large_struct = {}
        for i in range(1000):
            large_struct[f"resource_{i}"] = {
                "type": f"service_{i % 10}",  # 10種類のサービスタイプ
                "config": {"nested": {"type": f"nested_service_{i % 5}"}},
            }

        start_time = time.time()
        resource_types = list(find_resource_types(large_struct))
        end_time = time.time()

        # 1秒以内で完了することを確認
        assert (end_time - start_time) < 1.0

        # 正しい数のリソースタイプが抽出されることを確認
        assert len(resource_types) == 2000  # 1000 * 2 (main + nested)

    def test_deep_nesting_performance(self):
        """深いネスト構造でのパフォーマンステスト"""
        # 深くネストされた構造を生成
        deep_struct = {"type": "root"}
        current = deep_struct

        for i in range(100):
            current["nested"] = {"type": f"level_{i}", "data": {}}
            current = current["nested"]["data"]

        start_time = time.time()
        resource_types = list(find_resource_types(deep_struct))
        end_time = time.time()

        # 1秒以内で完了することを確認
        assert (end_time - start_time) < 1.0

        # 正しい数のリソースタイプが抽出されることを確認
        assert len(resource_types) == 101  # root + 100 levels

    def test_cost_calculation_performance(self):
        """コスト計算のパフォーマンステスト"""
        # 大量のリソースタイプを含む構造
        struct_data = {}
        costs_db = {}

        for i in range(500):
            resource_type = f"service_{i}"
            struct_data[f"resource_{i}"] = {"type": resource_type}
            costs_db[resource_type] = {
                "cost": str(10.0 + (i * 0.1)),
                "type": "per_month" if i % 2 == 0 else "per_request",
            }

        start_time = time.time()
        result = calculate_final_cost(struct_data, costs_db, 10000)
        end_time = time.time()

        # 1秒以内で完了することを確認
        assert (end_time - start_time) < 1.0

        # 結果が正の値であることを確認
        assert result > 0

    def test_memory_usage_with_large_data(self):
        """大量データでのメモリ使用量テスト（簡易版）"""
        # 大量のデータを処理してもエラーが発生しないことを確認
        results = []

        for _ in range(10):
            large_struct = {}
            for i in range(1000):
                large_struct[f"resource_{i}"] = {
                    "type": f"service_{i % 20}",
                    "config": {"nested": {"type": f"nested_{i % 10}"}},
                }

            resource_types = list(find_resource_types(large_struct))
            results.append(len(resource_types))

        # 全ての処理が正常に完了することを確認
        assert len(results) == 10
        assert all(result > 0 for result in results)

    def test_concurrent_calculations(self):
        """並行計算のテスト"""
        import threading
        import queue

        def calculate_worker(q, struct_data, costs_db, num_requests):
            try:
                result = calculate_final_cost(struct_data, costs_db, num_requests)
                q.put(result)
            except Exception as e:
                q.put(e)

        struct_data = {"web": {"type": "ec2"}, "db": {"type": "rds"}}
        costs_db = {
            "ec2": {"cost": "10.0", "type": "per_month"},
            "rds": {"cost": "20.0", "type": "per_month"},
        }

        # 10個の並行スレッドで計算
        threads = []
        result_queue = queue.Queue()

        start_time = time.time()

        for i in range(10):
            thread = threading.Thread(
                target=calculate_worker,
                args=(result_queue, struct_data, costs_db, 1000 * (i + 1)),
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        end_time = time.time()

        # 5秒以内で完了することを確認
        assert (end_time - start_time) < 5.0

        # 全ての結果が正常であることを確認
        results = []
        while not result_queue.empty():
            result = result_queue.get()
            assert not isinstance(result, Exception)
            results.append(result)

        assert len(results) == 10

        # 結果が期待値と一致することを確認
        for i, result in enumerate(results):
            expected = 30.0  # ec2(10) + rds(20)
            assert result == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
