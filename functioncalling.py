from google import genai
from google.genai import types
import datetime

# Define the function declaration for the model
from google.genai import types

time_function_declaration = types.FunctionDeclaration(
    name="get_current_time",
    description="Get the current time in the local timezone.",
    parameters={"type": "object", "properties": {}, "required": []}
)


# Function to retrieve the current time
def get_current_time():
    """
    Returns the current time in the local timezone as a string.
    """
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    return f"The current time is {current_time} in your local timezone."