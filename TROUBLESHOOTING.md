# Troubleshooting Guide - Pokemon Card Scanner

This guide helps you fix common issues with card scanning and improve accuracy.

## Quick Diagnostic

**Run this first:**
```bash
python diagnostic.py
```

This will check:
- Tesseract OCR installation
- Learning system status
- API connectivity
- Cache size

---

## Common Issues

### ❌ "Cannot get a single card right"

**Most likely cause:** Empty card cache means fuzzy matching is disabled.

**Solutions (in order):**

#### 1. Build the Card Cache (RECOMMENDED - Do this first!)

```
1. Open the scanner
2. Go to: Learning > Build Card Cache
3. Click "Yes" to fetch popular cards
4. Wait ~1 minute for 200+ cards to be cached
5. Try scanning again
```

**Why this helps:** The fuzzy matching system needs a database of card names to match against. Without it, the system can only use raw OCR extraction which is often imperfect.

#### 2. Check Debug Output

Look at the terminal/console output when scanning:

```
============================================================
[OCR] Raw extracted text:
<text will appear here>
============================================================

[OCR] Extracted card name: 'CardName'
[Main] Trying fuzzy match with cache size: 234
[Fuzzy Match] Found 5 matches for 'CardName' (threshold: 0.3)
[Fuzzy Match] Top match: 'Card Name' (85.0%)
```

**What to look for:**
- Is OCR extracting ANY text? If not, camera/lighting issue
- Is a card name extracted? If not, OCR issue
- What's the cache size? If 0, build the cache!
- Are fuzzy matches being found? If not, lower threshold or add more cards

#### 3. Improve OCR Quality

**Better lighting:**
- Use bright, even lighting
- Avoid shadows on the card
- Avoid glare/reflections

**Better positioning:**
- Hold card flat and still
- Fill most of the camera view
- Keep card name area in focus
- Try different angles

**Camera settings:**
- Make sure camera is focused
- Try cleaning camera lens
- Ensure adequate resolution

#### 4. Manual Correction (Teaches the System)

When OCR fails:
```
1. Scan the card (even if it fails)
2. Go to: Learning > Correct Last Scan
3. Enter the correct card name
4. Click "Submit Correction"
```

**Next time:** The system will recognize that OCR pattern automatically!

---

## Understanding the Learning System

### How It Gets Smarter

1. **First Scan:** Uses raw OCR + fuzzy matching
2. **After Correction:** Learns the OCR → Card Name mapping
3. **Subsequent Scans:** Automatically recognizes learned patterns

### Thresholds Explained

The scanner uses these similarity thresholds:

- **0.9 - 1.0 (90-100%)**: Exact or near-exact match
- **0.7 - 0.9 (70-90%)**: Very good match
- **0.5 - 0.7 (50-70%)**: Good match
- **0.3 - 0.5 (30-50%)**: Acceptable match ✓ (current threshold)
- **< 0.3 (< 30%)**: Rejected

**Default thresholds (after improvements):**
- Fuzzy matching: 30% (very lenient)
- Learned patterns: 30% (very lenient)
- Word overlap: Automatically boosts scores

### Cache Size Matters

| Cache Size | Fuzzy Matching Quality |
|------------|----------------------|
| 0 cards    | ❌ Disabled          |
| 1-50       | ⚠️ Limited          |
| 50-200     | ✓ Good              |
| 200-500    | ✓✓ Very Good        |
| 500+       | ✓✓✓ Excellent       |

**Recommendation:** Build cache to get at least 200 cards.

---

## Specific Error Messages

### "No text detected"

**Causes:**
- Camera focus issue
- Card too far/blurry
- Extremely poor lighting
- Tesseract not installed

**Solutions:**
1. Run `python diagnostic.py` to check Tesseract
2. Improve lighting
3. Move card closer to camera
4. Ensure camera is focused

---

### "Could not identify card name"

**If cache is 0:**
```
💡 TIP: Build the card cache first!
Go to 'Learning > Build Card Cache'
```

**If cache > 0:**
```
Use 'Learning > Correct Last Scan' to teach the system
```

**Debug steps:**
1. Look at the OCR text shown in the error
2. Is it readable? If yes → correction will help
3. If it's gibberish → improve camera/lighting
4. Check cache size in statistics

---

### "No cards found" (after successful OCR)

**Causes:**
- Card name is misspelled in OCR
- Fuzzy matching didn't find close enough match
- Card is very rare/new and not in API

**Solutions:**
1. Use manual search with correct name
2. Correct the OCR scan to teach system
3. Check if card exists on pokemontcg.io

---

## Advanced Troubleshooting

### Viewing Learning Statistics

```
1. Learning > View Statistics
2. Check:
   - Cached cards (should be > 100)
   - Success rate (improves over time)
   - Learned patterns (grows with use)
```

### Debug Logging

The scanner prints detailed logs. Look for:

```
[OCR] Extracted card name: 'Pikachu'
[Main] Extracted card name from OCR: 'Pikachu'
[Main] Trying fuzzy match with cache size: 234
[Fuzzy Match] Found 12 matches for 'Pika' (threshold: 0.3)
[Fuzzy Match] Top match: 'Pikachu' (95.0%)
[Main] Using fuzzy match: Pikachu (95%)
```

**Problem indicators:**
- No text extracted → Camera/OCR issue
- Cache size 0 → Build cache!
- No fuzzy matches → Lower threshold or add corrections
- API errors → Internet/API issue

### OCR Accuracy Tips

**Good OCR depends on:**
1. ✓ Bright, even lighting
2. ✓ Sharp focus
3. ✓ Flat card (no bending)
4. ✓ Clean card surface
5. ✓ Steady hand/camera
6. ✓ Proper camera angle (perpendicular to card)

**Avoid:**
1. ✗ Shadows
2. ✗ Glare/reflections
3. ✗ Blurry images
4. ✗ Extreme angles
5. ✗ Poor lighting

---

## Performance Optimization

### Building a Better Cache

**Default cache (200 cards):**
```
Learning > Build Card Cache
```

**Manual cache building:**
```python
# Search for specific Pokemon to cache
1. Manually search for cards you own
2. System automatically caches results
3. Cache grows organically with use
```

**Best practice:**
- Build cache once at first use
- Let it grow naturally as you search
- Periodically search for new releases

### Success Rate Tracking

Monitor improvement:
```
1. Learning > View Statistics
2. Check "Success Rate"
3. Should increase over time:
   - Day 1: ~20-40% (no cache/patterns)
   - Day 7: ~60-80% (with cache)
   - Day 30: ~90%+ (with corrections)
```

---

## Still Having Issues?

### Check Your Setup

1. **Tesseract Installed?**
   ```bash
   python diagnostic.py
   ```

2. **Cache Built?**
   ```
   Learning > View Statistics
   Look for "Cached Cards" count
   ```

3. **API Working?**
   - Try manual search for "Pikachu"
   - Should find many cards

### Get More Help

**Debug information to collect:**
1. Output of `python diagnostic.py`
2. Console output when scanning
3. Screenshot of OCR text in error message
4. Learning statistics screenshot
5. Tesseract version

### Common Mistakes

❌ **Not building the cache first**
   → Fuzzy matching won't work

❌ **Not correcting failed scans**
   → System can't learn

❌ **Poor lighting/focus**
   → OCR extracts gibberish

❌ **Expecting 100% accuracy immediately**
   → System needs to learn your cards

✓ **Correct approach:**
1. Build cache (one time)
2. Scan cards with good lighting
3. Correct failures to teach system
4. Accuracy improves over time

---

## Success Tips

### For Best Results:

1. **Day 1:** Build cache, scan 10 cards, correct failures
2. **Day 2-7:** Continue scanning, corrections become rare
3. **Day 7+:** System recognizes most cards automatically

### Measuring Success:

```
Learning > View Statistics

Target metrics:
- Cached cards: 200+
- Success rate: 70%+
- Learned patterns: 20+
- High confidence patterns: 10+
```

### Remember:

> The scanner is a **learning system**. It gets smarter with every scan and every correction. One-time setup (building cache) + a few corrections = excellent accuracy!

---

## Quick Reference

| Issue | Solution |
|-------|----------|
| No matches | Build card cache |
| Poor OCR | Improve lighting/focus |
| Repeated failures | Use corrections |
| API errors | Check internet |
| Low success rate | Build cache + corrections |
| System not learning | Check statistics |

**Most important:** Build the cache first! Everything else builds on that foundation.
