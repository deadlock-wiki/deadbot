import os
from dotenv import load_dotenv

load_dotenv()

# Inches per meter, as engine units are inches
ENGINE_UNITS_PER_METER = 1 / 0.0254
OUTPUT_DIR = os.getenv('OUTPUT_DIR', '../../output-data/')
