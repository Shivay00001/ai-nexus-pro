import argparse
import asyncio
import logging
import sys
from goatclaw.runner import run_demo, run_parallel_demo
from goatclaw.worker import Worker
from goatclaw.orchestrator import Orchestrator
from goatclaw.core.structs import TaskGraph, TaskNode, AgentType, ExecutionMode
from goatclaw.init_db import init_db

def setup_cli_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

async def start_worker(worker_id: str):
    print(f"[*] Starting GOATCLAW Worker: {worker_id}")
    worker = Worker(worker_id=worker_id)
    await worker.setup()
    await worker.run()

async def submit_simple_goal(goal: str, distributed: bool):
    from goatclaw.agents.planner_agent import PlannerAgent
    from goatclaw.runner import create_orchestrator, create_default_security_context
    
    print(f"[!] Submitting Goal: {goal}")
    # Create production-grade orchestrator with all agents
    orch = create_orchestrator({"distributed": distributed})
    planner = PlannerAgent(orch.event_bus)
    
    await orch.start()
    
    try:
        sec_ctx = create_default_security_context()
        
        # 1. Plan the goal dynamically
        print("[*] Planning task graph...")
        graph = await planner.plan(goal, sec_ctx)
        
        if distributed:
            graph.execution_mode = ExecutionMode.DISTRIBUTED
            
        # 2. Execute the plan
        print(f"[*] Executing {len(graph.nodes)} planned nodes...")
        result = await orch.process_goal(graph, sec_ctx)
        
        print("\n[SUCCESS] Execution Finished!")
        print(f"Status: {result['status']}")
        print(f"Completed Nodes: {len(result['completed_nodes'])}/{result['total_nodes']}")
        
        if result["errors"]:
            print("\n[!] Errors encountered:")
            for err in result["errors"]:
                print(f"- {err['node_id']}: {err['error']}")
    finally:
        await orch.stop()

def main():
    parser = argparse.ArgumentParser(description="GOATCLAW CLI - Enterprise Agent Orchestrator")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run Demo
    demo_parser = subparsers.add_parser("demo", help="Run the core system demo")
    demo_parser.add_argument("--parallel", action="store_true", help="Run parallel execution demo")
    
    # Start Worker
    worker_parser = subparsers.add_parser("worker", help="Start a distributed worker node")
    worker_parser.add_argument("--id", type=str, default=None, help="Custom worker ID")
    
    # Run Chaos
    subparsers.add_parser("chaos", help="Run the resilience chaos testing suite")
    
    # Process Goal
    goal_parser = subparsers.add_parser("run", help="Execute a specific goal")
    goal_parser.add_argument("goal", type=str, help="The goal to achieve")
    goal_parser.add_argument("--distributed", action="store_true", help="Run in distributed mode")

    # Init DB
    subparsers.add_parser("init", help="Initialize the production database")

    args = parser.parse_args()
    setup_cli_logging(args.verbose)
    
    if args.command == "demo":
        if args.parallel:
            asyncio.run(run_parallel_demo())
        else:
            asyncio.run(run_demo())
            
    elif args.command == "worker":
        asyncio.run(start_worker(args.id))
        
    elif args.command == "chaos":
        from chaos_runner import ChaosRunner
        runner = ChaosRunner()
        asyncio.run(runner.start())
        
    elif args.command == "run":
        asyncio.run(submit_simple_goal(args.goal, args.distributed))
        
    elif args.command == "init":
        asyncio.run(init_db())
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
