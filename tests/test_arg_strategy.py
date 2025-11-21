import pytest
from core.executor import Executor

class TestArgStrategy:
    
    @pytest.fixture
    def executor(self, tmp_path):
        """创建一个干净的 Executor 用于测试参数逻辑"""
        return Executor(root_dir=tmp_path, yolo=True)

    def test_default_hybrid_behavior(self, executor):
        """测试默认的混合模式 (allow_hybrid=True)"""
        received_args = []
        
        def mock_hybrid_act(exc, args):
            received_args.extend(args)
            
        # 注册默认为 True
        executor.register("hybrid_op", mock_hybrid_act, allow_hybrid=True)
        
        statements = [{
            "act": "hybrid_op inline_arg",
            "contexts": ["block_arg"]
        }]
        
        executor.execute(statements)
        
        # 预期：两者合并
        assert received_args == ["inline_arg", "block_arg"]

    def test_strict_mode_with_inline(self, executor):
        """测试严格模式：有行内参数时，应忽略 Block"""
        received_args = []
        
        def mock_strict_act(exc, args):
            received_args.extend(args)
            
        # 显式注册为 False
        executor.register("strict_op", mock_strict_act, allow_hybrid=False)
        
        statements = [{
            "act": "strict_op inline_arg",
            "contexts": ["ignored_block_arg"]
        }]
        
        executor.execute(statements)
        
        # 预期：只保留行内参数，Block 被丢弃
        assert received_args == ["inline_arg"]

    def test_strict_mode_without_inline(self, executor):
        """测试严格模式：没有行内参数时，应接受 Block"""
        received_args = []
        
        def mock_strict_act(exc, args):
            received_args.extend(args)
            
        executor.register("strict_op", mock_strict_act, allow_hybrid=False)
        
        # act 字符串没有参数
        statements = [{
            "act": "strict_op",
            "contexts": ["valid_block_arg"]
        }]
        
        executor.execute(statements)
        
        # 预期：接受 Block
        assert received_args == ["valid_block_arg"]

    def test_strict_mode_multi_inline(self, executor):
        """测试严格模式：多个行内参数的情况"""
        received_args = []
        
        def mock_strict_act(exc, args):
            received_args.extend(args)
            
        executor.register("strict_op", mock_strict_act, allow_hybrid=False)
        
        statements = [{
            "act": "strict_op arg1 arg2",
            "contexts": ["ignored"]
        }]
        
        executor.execute(statements)
        
        assert received_args == ["arg1", "arg2"]
