import warnings

# LangChain still imports pydantic.v1 internally; harmless on Python 3.14.
warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    category=UserWarning,
)
