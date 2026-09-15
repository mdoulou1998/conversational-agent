"""Minimal agent loop: message -> decide -> validate -> execute, terminating sensibly.

Going to be built using (Google) SDK, instead of using a framework. This is to ensure full ownership of the agent loop,
1. Agent Loop Requiremnt - it will allow me to control when the loop terminates and the defn of sensible termination. 
I will be able to define the termination conditions and the logic for when the loop should stop, which is crucial for ensuring that the agent behaves as expected and doesn't run indefinitely.

2. Multi turn conversation - I will build the conversation history and pass this through to the agent.
Langchain memory class is an option, but I will build my own memory class to have more control over the conversation history and how it is managed. 
This will allow me to customize the memory management to fit the specific needs of my agent loop.

3. Tool call validation - I will validate the tool call before they are executed by the agent.
I need full visibility to validate the tools instead of building a custom callbacks for the langchain framework.

4. Evaluation - yet to fully understand.
"""