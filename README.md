# YouTube Economic Content Clipper

A powerful AI-driven tool for extracting economic insights from YouTube videos and creating shareable 30-60 second clips for social media content creation.

## 🎯 Overview

This application transforms long-form economic insight videos from YouTube into organized, shareable clips. Perfect for content creators focused on economic analysis, market commentary, and financial news.

### Key Features

- **YouTube Video Discovery**: Search and select from economic content
- **AI-Powered Transcription**: Full video transcription using OpenAI Whisper
- **Intelligent Clip Extraction**: GPT-4 analyzes transcripts to identify precise segments
- **Automated Processing**: Extract clips with optimal timing and format
- **Topic Organization**: Automatically categorize clips by economic topics
- **Multiple Formats**: Support for 16:9 (YouTube) and 9:16 (mobile) aspect ratios
- **Subtitle Integration**: Optional subtitle burning for improved accessibility

## 🚀 Quick Start

### Prerequisites

1. **FFmpeg**: Video processing engine
   ```bash
   # macOS
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt update && sudo apt install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

2. **Python 3.8+**: Required for the application

3. **API Keys**:
   - OpenAI API key (for Whisper and GPT-4)
   - YouTube Data API v3 key

### Installation

#### Option 1: Automatic Installation (Recommended)

**Linux/macOS:**
```bash
git clone <repository-url>
cd youtube-clipper
./install.sh
```

**Windows:**
```cmd
git clone <repository-url>
cd youtube-clipper
install.bat
```

#### Option 2: Manual Installation

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd youtube-clipper
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit .env with your API keys
   nano .env  # or use your preferred editor
   ```

3. **Run the application**:
   ```bash
   python -m youtube_clipper.main
   ```

## 🔧 Configuration

### API Keys Setup

#### OpenAI API Key
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Add to `.env` file as `OPENAI_API_KEY=your_key_here`

#### YouTube Data API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable YouTube Data API v3
4. Create credentials (API Key)
5. Add to `.env` file as `YOUTUBE_API_KEY=your_key_here`

### Directory Structure

The application creates these directories automatically:

```
youtube-clipper/
├── downloads/          # Temporary video storage
├── transcriptions/     # Full transcripts and SRT files
├── clips_output/       # Final processed clips
│   ├── inflation/      # Inflation-related clips
│   ├── fed/           # Federal Reserve content
│   ├── markets/       # Market analysis clips
│   ├── gdp/           # GDP and growth clips
│   ├── employment/    # Jobs and unemployment
│   ├── banking/       # Banking and credit
│   ├── crypto/        # Cryptocurrency content
│   ├── housing/       # Real estate and housing
│   ├── international/ # Global economic content
│   └── general/       # Uncategorized content
└── logs/              # Application logs
```

## 📋 Usage Guide

### Basic Workflow

1. **Search for Videos**:
   - Enter economic topics like "Fed rate decision 2024" or "inflation analysis"
   - Select from search results

2. **Describe Your Clip**:
   - Use natural language: "the part about quantitative easing effects"
   - Be specific: "his take on the latest jobs report"
   - General: "the inflation discussion"

3. **Choose Options**:
   - Aspect ratio: 16:9 (YouTube) or 9:16 (mobile/vertical)
   - Subtitles: yes/no
   - Quality: fast/medium/high

4. **Get Your Clip**:
   - Automatically organized by topic
   - Ready for social media sharing

### Example Usage Session

```
Enter YouTube search query: Fed interest rate decision December 2024

Search Results:
1. Fed Cuts Rates: What This Means for Markets
   Channel: Economic Insights TV

Select a video (1-1): 1

Describe the clip you want: the part where they explain the impact on housing markets

Analyzing transcription to find clip timestamps...
Found clip: 145.2s to 198.7s (duration: 53.5s)

Aspect ratio (16:9 or 9:16) [default: 16:9]: 16:9
Add subtitles? (y/n) [default: n]: y

Processing clip for topic: fed
Creating video clip...

✅ Successfully created clip: clips_output/fed/video_clip_145s_198s.mp4
   Duration: 53.5 seconds
   Category: fed
   Format: 16:9
```

### Advanced Features

#### Topic Categories

The system automatically categorizes clips into economic topics:

- **Inflation**: CPI, PPI, price analysis, cost discussions
- **Fed**: Federal Reserve, interest rates, monetary policy, Jerome Powell
- **Markets**: Stock market, bonds, trading, investment, portfolio analysis
- **GDP**: Economic growth, recession, expansion, output data
- **Employment**: Jobs reports, unemployment, labor market, workforce
- **Banking**: Banking sector, credit, lending, financial institutions
- **Crypto**: Cryptocurrency, digital assets, blockchain regulation
- **Housing**: Real estate, mortgage rates, housing market trends
- **International**: Global economy, trade, foreign markets
- **General**: Uncategorized economic content

#### Clip Description Tips

**Effective descriptions**:
- "the explanation of how inflation affects bond yields"
- "when they discuss the unemployment rate changes"
- "the part about cryptocurrency regulation"
- "his analysis of the housing market data"

**Less effective descriptions**:
- "the good part" (too vague)
- "everything" (too broad)
- "minute 5" (use specific content instead)

## 🛠️ Technical Details

### Architecture Overview

The system follows a modular pipeline architecture:

1. **YouTube API Integration**: Video search and metadata retrieval
2. **Video Download**: Pytube-based downloading with format selection
3. **AI Transcription**: OpenAI Whisper for high-accuracy transcription
4. **Clip Identification**: GPT-4 analysis of transcripts for timestamp detection
5. **Video Processing**: FFmpeg-based clipping, formatting, and subtitle integration
6. **Organization**: Topic-based categorization and file management

### Performance Characteristics

- **Search to Selection**: < 10 seconds
- **Download + Transcription**: 2-5 minutes (varies by video length)
- **Clip Identification**: 10-30 seconds
- **Final Processing**: 30-60 seconds
- **Total Pipeline**: 3-7 minutes per clip

### Quality Settings

The application balances speed and quality:

- **Video Codec**: H.264 (libx264) with CRF 23
- **Audio Codec**: AAC at 128kbps
- **Processing**: Medium preset for balanced speed/quality
- **Output Resolution**: 1080p for 16:9, 720x1280 for 9:16

## 🔍 Troubleshooting

### Common Issues

#### "FFmpeg not found"
```bash
# Install FFmpeg (see Prerequisites section)
# Verify installation
ffmpeg -version
```

#### "API key not found"
```bash
# Check .env file exists and contains keys
cat .env

# Verify environment variables are loaded
python -c "import os; print(os.getenv('OPENAI_API_KEY', 'NOT FOUND'))"
```

#### "No suitable stream found"
- Some videos may have restricted download permissions
- Try a different video from the search results
- Check if the video is age-restricted or region-locked

#### "Could not determine timestamps"
- Try a more specific clip description
- Ensure the content actually exists in the video
- Check the transcription file for accuracy

#### "Transcription failed"
- Video file may be corrupted
- Audio quality might be too poor
- File size may exceed Whisper API limits (25MB)

### Logging and Debugging

Application logs are saved to `logs/youtube_clipper.log`:

```bash
# View recent logs
tail -f logs/youtube_clipper.log

# Search for errors
grep ERROR logs/youtube_clipper.log
```

### API Rate Limits

Be aware of service limitations:

- **OpenAI Whisper**: File size limit of 25MB
- **OpenAI GPT-4**: Rate limits based on your plan
- **YouTube Data API**: Daily quota limits (default: 10,000 units)

## 📊 Cost Considerations

### API Usage Costs

**OpenAI Costs** (approximate):
- Whisper transcription: ~$0.006 per minute of audio
- GPT-4 analysis: ~$0.03-0.06 per request
- **Daily usage example**: 5 clips = ~$0.50-1.00

**YouTube Data API**:
- Free tier: 10,000 units/day
- Search request: 100 units
- **Daily usage**: 5 searches = 500 units (well within limits)

### Cost Optimization Tips

1. **Reuse transcriptions** for multiple clips from the same video
2. **Use specific descriptions** to reduce GPT-4 retries
3. **Monitor API usage** through provider dashboards
4. **Batch processing** when possible

## 🔒 Security and Privacy

### Data Handling

- **Local Processing**: All video files processed locally
- **No Cloud Storage**: Videos deleted after processing
- **API Communications**: Only transcription and analysis data sent to APIs
- **No Personal Data**: System doesn't store user information

### Best Practices

1. **Keep API keys secure**: Never commit `.env` files
2. **Regular key rotation**: Update API keys periodically
3. **Monitor usage**: Check for unexpected API calls
4. **Respect copyright**: Use for personal/educational purposes

## 🚧 Limitations and Known Issues

### Current Limitations

1. **Video Length**: Large videos (>1 hour) may have processing issues
2. **Timestamp Accuracy**: AI may be off by 5-10 seconds (manual trimming expected)
3. **Language Support**: Optimized for English economic content
4. **Audio Quality**: Poor audio affects transcription accuracy
5. **Processing Time**: Real-time processing not possible

### Planned Improvements

- [ ] Batch processing for multiple videos
- [ ] Enhanced topic classification
- [ ] Custom clip templates
- [ ] Preview mode before final processing
- [ ] Multiple output quality presets

## 🤝 Contributing

### Development Setup

```bash
# Install development dependencies
pip install pytest black flake8 mypy

# Run tests
pytest tests/

# Format code
black youtube_clipper/

# Lint code
flake8 youtube_clipper/

# Type checking
mypy youtube_clipper/
```

### Project Structure

```
youtube_clipper/
├── __init__.py
├── main.py              # Main application entry point
├── config.py            # Configuration management
├── core/                # Core business logic
│   ├── youtube_search.py
│   ├── video_downloader.py
│   ├── transcriber.py
│   ├── clip_finder.py
│   ├── video_processor.py
│   └── topic_classifier.py
├── utils/               # Utility modules
│   ├── logger.py
│   ├── file_manager.py
│   └── validators.py
└── exceptions/          # Custom exceptions
    └── custom_exceptions.py
```

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **OpenAI** for Whisper and GPT-4 APIs
- **Google** for YouTube Data API
- **FFmpeg** team for video processing capabilities
- **Python community** for excellent libraries

## Support

### Getting Help

1. **Check this README** for common solutions
2. **Review logs** in `logs/youtube_clipper.log`
3. **Run diagnostics**: `python scripts/check_dependencies.py`
4. **Validate config**: `python scripts/validate_config.py`

### Reporting Issues

When reporting issues, please include:

- Operating system and Python version
- Full error message and stack trace
- Steps to reproduce the problem
- API key status (without revealing actual keys)
- Log file contents (relevant sections)

---

**Happy clipping! **

Transform your long-form economic content into engaging, shareable clips that drive your social media strategy forward.
