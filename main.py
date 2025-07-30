#!/usr/bin/env python3
"""
Alpha Machine - AI-powered transcript processing and Linear ticket generation.

Main entry point for the application.
"""

from src.flows.linear_flow.orchestrator import AlphaMachineOrchestrator
from src.core.utils import print_separator


def main():
    """Main entry point for Alpha Machine."""
    try:
        # Initialize orchestrator
        orchestrator = AlphaMachineOrchestrator()
        
        # Run the full workflow
        result = orchestrator.run_full_workflow()
        
        if result["success"]:
            print_separator("WORKFLOW COMPLETED SUCCESSFULLY")
            return 0
        else:
            print_separator("WORKFLOW FAILED")
            print(f"Error: {result['error']}")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
