"""Visualize the LangGraph workflow."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from edumentor.agents.orchestrator import AgentOrchestrator
from edumentor.services.session import SessionService
from edumentor.services.profile import ProfileService

# Create orchestrator to initialize the graph
session_service = SessionService()
profile_service = ProfileService()
orchestrator = AgentOrchestrator(
    session_service=session_service,
    profile_service=profile_service
)

if orchestrator._flow is not None:
    print("LangGraph workflow initialized successfully!")
    print("\nGenerating graph visualization...")
    
    try:
        # Generate graph visualization
        from IPython.display import Image, display  # type: ignore
        
        # Get the graph as PNG
        graph_image = orchestrator._flow.get_graph().draw_mermaid_png()
        
        # Save to file
        output_path = project_root / "langgraph_visualization.png"
        with open(output_path, "wb") as f:
            f.write(graph_image)
        
        print(f"✅ Graph visualization saved to: {output_path}")
        
    except ImportError:
        print("⚠️  IPython not available. Trying alternative visualization...")
        
        try:
            # Try mermaid text format
            mermaid_code = orchestrator._flow.get_graph().draw_mermaid()
            
            # Save mermaid code
            output_path = project_root / "langgraph_visualization.mmd"
            with open(output_path, "w") as f:
                f.write(mermaid_code)
            
            print(f"✅ Mermaid diagram saved to: {output_path}")
            print("\nMermaid code:")
            print("-" * 80)
            print(mermaid_code)
            print("-" * 80)
            print("\nYou can visualize this at: https://mermaid.live/")
            
        except Exception as e:
            print(f"❌ Failed to generate mermaid diagram: {e}")
            
            # Fallback: Print text representation
            print("\nGraph structure (text representation):")
            print("-" * 80)
            print("Nodes:")
            print("  - tutor (entry point)")
            print("  - planner")
            print("\nConditional Edges:")
            print("  tutor → [route_message]")
            print("    → 'planner' → planner node")
            print("    → 'tutor' → END")
            print("\nEdges:")
            print("  planner → END")
            print("-" * 80)
    
    except Exception as e:
        print(f"❌ Error generating visualization: {e}")
        
        # Fallback: Print text representation
        print("\nGraph structure (text representation):")
        print("-" * 80)
        print("Nodes:")
        print("  - tutor (entry point)")
        print("  - planner")
        print("\nConditional Edges:")
        print("  tutor → [route_message]")
        print("    → 'planner' → planner node")
        print("    → 'tutor' → END")
        print("\nEdges:")
        print("  planner → END")
        print("-" * 80)
else:
    print("❌ LangGraph is not initialized. The graph visualization is not available.")
    print("\nFallback routing logic is being used instead.")
