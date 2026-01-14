# Pokemon Card Scanner

A comprehensive Pokemon Trading Card Game (TCG) scanner that uses your camera to scan physical cards, extracts information using OCR, retrieves detailed card data and pricing from the Pokemon TCG API, and saves all information to organized files.

## Features

### Core Scanning
- 📷 **Camera Integration**: Real-time camera feed for scanning physical Pokemon cards with multi-camera support
- 🎯 **Perspective Transformation**: Automatically detects card edges and straightens tilted/angled cards before OCR
- 🔍 **OCR Text Extraction**: Automatic text recognition from card images using Tesseract
- 🌐 **TCG API Integration**: Fetches comprehensive card data from the official Pokemon TCG API
- 💰 **Pricing Information**: Retrieves current market prices from TCGPlayer (USD) and Cardmarket (EUR)
- 📊 **Detailed Card Info**: Displays HP, types, abilities, attacks, weaknesses, resistances, rarity, and more
- 💾 **File Management**: Saves card data in multiple formats (JSON, TXT) with images
- 🖥️ **Dual Interface**: Both GUI and command-line interfaces available
- 🔎 **Manual Search**: Search for cards by name even without scanning
- 🎥 **Camera Selection**: Choose from multiple connected cameras (webcam, phone, external cameras)

### 🧠 **Intelligent Learning System** (NEW!)
- **Auto-Improving Accuracy**: Gets smarter with every scan
- **Card Name Caching**: Builds local database of Pokemon cards for instant fuzzy matching
- **OCR Pattern Learning**: Remembers successful scans and reuses patterns
- **User Corrections**: One-time corrections permanently teach the system
- **Fuzzy Matching**: Finds cards even when OCR isn't perfect (40% similarity threshold)
- **Statistics Tracking**: Monitor success rate and learning progress
- **Multiple Matching Strategies**: 5 different algorithms to find the right card

**See [LEARNING_SYSTEM.md](LEARNING_SYSTEM.md) for complete details.**

## API Documentation

This project uses the [Pokemon TCG API](https://pokemontcg.io/):
- **GitHub**: https://github.com/PokemonTCG/pokemon-tcg-api-docs
- **Python SDK**: https://github.com/PokemonTCG/pokemon-tcg-sdk-python
- **Base URL**: `https://api.pokemontcg.io/v2/`

## Requirements

- Python 3.9+
- Camera/Webcam
- Tesseract OCR installed on your system
- Internet connection for API access

## Installation

### 1. Install Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

### 2. Clone the Repository

```bash
git clone https://github.com/Funkeymantic/TCGPokemon.git
cd TCGPokemon
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API Key (Optional but Recommended)

Get a free API key from https://dev.pokemontcg.io/ for higher rate limits.

Create a `.env` file in the project root:
```bash
cp .env.example .env
```

Edit `.env` and add your API key:
```
POKEMONTCG_IO_API_KEY=your_api_key_here
```

## Usage

### Quick Start with Learning System 🚀

**For best results, do this FIRST:**

```bash
# 1. Run diagnostic to check setup
python diagnostic.py

# 2. Start the scanner
python src/main.py

# 3. Build the card cache (ONE TIME SETUP)
#    In the app: Learning > Build Card Cache
#    Wait ~1 minute for 200+ cards to be cached

# 4. Start scanning!
```

**Why build the cache?** It enables intelligent fuzzy matching, making the scanner much more accurate even when OCR isn't perfect.

### GUI Application

Run the graphical interface:
```bash
python src/main.py
```

**GUI Features:**
1. **Camera Selection**: Choose from available cameras using dropdown (webcam, phone via Iriun, external cameras)
   - Use "Refresh" button to detect newly connected cameras
2. **Start Camera**: Begin camera feed with automatic perspective correction
3. **Capture & Scan**: Take a picture and automatically scan for card information
   - Card edges are detected and image is straightened automatically
4. **Manual Search**: Search for cards by typing the name
5. **Learning Menu**:
   - **Build Card Cache**: One-time setup for fuzzy matching (RECOMMENDED!)
   - **View Statistics**: See success rate and learning progress
   - **Correct Last Scan**: Teach the system when OCR fails
6. **View Results**: See all matching cards in the results list
7. **Filter Results**: Search through results with the filter box
8. **Select Card**: Click on a result to view detailed information and card image
9. **Save Data**: Save all card information to files

### Command-Line Interface

Run the CLI version:
```bash
python scan_card.py
```

**CLI Controls:**
- `SPACE`: Capture image and scan card
- `s`: Manual search by card name
- `q`: Quit application

## Project Structure

```
TCGPokemon/
├── src/
│   ├── __init__.py           # Package initialization
│   ├── main.py               # GUI application
│   ├── camera_capture.py     # Camera operations
│   ├── ocr_processor.py      # OCR text extraction
│   ├── tcg_api.py            # Pokemon TCG API integration
│   ├── card_display.py       # Card information formatting
│   └── file_manager.py       # File saving operations
├── scan_card.py              # CLI application
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

## Saved Files

When you save a card, the following files are created in the `card_data/` directory:

1. **`{card_name}_{timestamp}.json`** - Complete card data in JSON format
2. **`{card_name}_info_{timestamp}.txt`** - Human-readable card information
3. **`{card_name}_pricing_{timestamp}.txt`** - Detailed pricing information
4. **`{card_name}_large_{timestamp}.png`** - High-resolution card image
5. **`{card_name}_small_{timestamp}.png`** - Small card image

## Card Information Retrieved

The application retrieves and displays:

- **Basic Info**: Name, ID, HP, Type, Supertype, Subtypes
- **Abilities**: All abilities with descriptions
- **Attacks**: Attack names, costs, damage, and effects
- **Stats**: Weaknesses, resistances, retreat cost
- **Set Info**: Set name, series, card number, release date, rarity
- **Legalities**: Tournament format legalities (Standard, Expanded, Unlimited)
- **Pricing**: TCGPlayer and Cardmarket prices (normal and holofoil variants)
- **Artwork**: Official card images
- **Metadata**: Artist name, flavor text, regulation marks

## How It Works

1. **Image Capture**: Camera captures image of Pokemon card
2. **Image Processing**:
   - Card region detection using edge detection
   - Image enhancement (contrast, sharpening)
   - Preprocessing for OCR
3. **Text Extraction**: Tesseract OCR extracts text from the card
4. **Name Recognition**: Algorithm identifies the Pokemon name from extracted text
5. **API Search**: Queries Pokemon TCG API with card name
6. **Data Retrieval**: Fetches complete card information including pricing
7. **Display**: Shows formatted information to user
8. **Save**: Exports data to multiple file formats

## Troubleshooting

### Camera Not Working
- Ensure your camera is connected and not being used by another application
- Try changing the camera index in the code (default is 0)
- Check camera permissions on your operating system

### OCR Not Detecting Text
- Ensure Tesseract is properly installed and in your PATH
- Improve lighting conditions when scanning cards
- Position the card to fill more of the camera frame
- Try adjusting the card angle to reduce glare

### No Cards Found in API
- Verify internet connection
- Check if the card name was correctly identified (shown in console)
- Try manual search with the exact card name
- Some promotional or very new cards might not be in the database

### Rate Limiting
- Get a free API key from https://dev.pokemontcg.io/
- Add the API key to your `.env` file
- Wait a moment between searches if hitting limits

## Dependencies

- **opencv-python**: Camera access and image processing
- **pytesseract**: OCR text extraction
- **pokemontcgsdk**: Pokemon TCG API wrapper
- **Pillow**: Image handling
- **requests**: HTTP requests for image downloads
- **python-dotenv**: Environment variable management

## API Rate Limits

Without API key: 1000 requests per day
With API key: 5000 requests per day

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is for educational and personal use. Pokemon and related trademarks are property of Nintendo, Game Freak, and The Pokemon Company.

## Acknowledgments

- [Pokemon TCG API](https://pokemontcg.io/) for providing the card database
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for text recognition
- The Pokemon community for their support

## Troubleshooting

### Card Recognition Not Working?

**Run the diagnostic first:**
```bash
python diagnostic.py
```

Common issues and solutions:

| Problem | Solution |
|---------|----------|
| ❌ "Cannot get cards right" | **Build the card cache!** Learning > Build Card Cache |
| ❌ "No text detected" | Improve lighting, focus, or check Tesseract installation |
| ❌ "No cards found" | Use "Learning > Correct Last Scan" to teach the system |
| ⚠️ Low accuracy | Build cache + correct a few scans = system learns quickly |
| 📉 Success rate < 50% | Cache size is probably 0 - build it! |

**See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for complete guide.**

### Quick Tips

1. **First time user?** Build the card cache before scanning (Learning > Build Card Cache)
2. **OCR failing?** Use Learning > Correct Last Scan - one correction teaches the system forever
3. **Want better accuracy?** Good lighting + focused camera + card cache = 90%+ success rate
4. **Monitoring progress?** Check Learning > View Statistics to see improvement

## Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Note**: This application requires a working camera and internet connection. Card recognition accuracy depends on image quality, lighting conditions, and card condition.