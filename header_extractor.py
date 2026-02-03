import pymupdf as fitz
import re
from collections import Counter

class HeaderExtractor:
    def __init__(self):
        # Standard dictionary of resume section headers
        self.HEADER_PATTERNS = [
            r"about me", r"academic history", r"achievements", r"affiliations", r"awards",
            r"career objective", r"certifications", r"contact", r"contact info", r"core competencies",
            r"courses", r"education", r"employment history", r"experience", r"hobbies", r"interests",
            r"languages", r"licenses", r"memberships", r"objective", r"professional associations",
            r"professional experience", r"professional summary", r"projects", r"publications",
            r"qualifications", r"references", r"skills", r"summary", r"technical skills",
            r"volunteer experience", r"volunteering", r"work experience"
        ]
        
        # --- Create a "Spaceless" Lookup Map ---
        self.SPACELESS_HEADERS = {h.replace(" ", ""): h for h in self.HEADER_PATTERNS}

    def _clean_text(self, text):
        """Normalizes text by removing punctuation and converting to lowercase."""
        return re.sub(r'[^\w\s]', '', text).lower().strip()

    def _get_lines_with_style(self, page):
        """Extracts lines with font metadata."""
        blocks = page.get_text("dict")["blocks"]
        lines = []

        for block in blocks:
            if "lines" not in block: continue
            for line in block["lines"]:
                line_text = ""
                spans = []
                for span in line["spans"]:
                    if span["text"].strip():
                        line_text += span["text"] + " "
                        spans.append(span)

                line_text = line_text.strip()
                if not line_text: continue
                
                if spans:
                    avg_size = sum(s["size"] for s in spans) / len(spans)
                    is_bold = any("bold" in s["font"].lower() for s in spans)
                    font_name = spans[0]["font"]
                else:
                    avg_size, is_bold, font_name = 0, False, "unknown"

                is_bullet = bool(re.match(r'^[\u2022\u2023\u25E6\u2043\u2219\-*]', line_text))
                
                lines.append({
                    "text": line_text,
                    "clean": self._clean_text(line_text),
                    "size": avg_size,
                    "is_bold": is_bold,
                    "is_upper": line_text.isupper() and len(line_text) > 3,
                    "is_bullet": is_bullet,
                    "y": line["bbox"][1],
                    "font": font_name,
                    "block_height": block["bbox"][3] - block["bbox"][1]
                })
        lines.sort(key=lambda x: x["y"])
        return lines

    def _merge_split_headers(self, lines):
        """Merges adjacent lines with same style ."""
        merged_lines = []
        i = 0
        while i < len(lines):
            current = lines[i]
            if i + 1 < len(lines):
                next_line = lines[i+1]
                same_style = (abs(current["size"] - next_line["size"]) < 0.5) and \
                             (current["is_bold"] == next_line["is_bold"]) and \
                             (current["is_upper"] == next_line["is_upper"])

                if same_style and (current["is_upper"] or current["is_bold"]):
                    combined_clean = current["clean"] + " " + next_line["clean"]
                    # Check regular match OR spaceless match for the merged line
                    combined_spaceless = combined_clean.replace(" ", "")
                    
                    if any(combined_clean == h for h in self.HEADER_PATTERNS) or \
                       (combined_spaceless in self.SPACELESS_HEADERS):
                        
                        current["text"] = current["text"] + " " + next_line["text"]
                        current["clean"] = combined_clean
                        merged_lines.append(current)
                        i += 2
                        continue
            merged_lines.append(current)
            i += 1
        return merged_lines

    def extract(self, pdf_path):
        doc = fitz.open(pdf_path)
        all_lines = []
        for page in doc:
            all_lines.extend(self._get_lines_with_style(page))

        all_lines = self._merge_split_headers(all_lines)

        if not all_lines: return [], 0, 0

        sizes = [round(l["size"], 1) for l in all_lines]
        body_size = Counter(sizes).most_common(1)[0][0]

        detected_headers = []
        final_headers = []

        target_size = None
        target_is_bold = None
        target_is_upper = None
        target_font_name = None

        while True:
            for line in all_lines:
                text = line["text"]
                clean = line["clean"]

                if line["is_bullet"]: continue
                if len(clean.split()) > 10: continue 

                score = 0

                # --- Spaceless Check ---
                spaceless_clean = clean.replace(" ", "")
                
                # A. Exact Keyword Match (Standard OR Spaceless)
                if clean in self.HEADER_PATTERNS:
                    score += 3
                elif spaceless_clean in self.SPACELESS_HEADERS:
                    print(f"DEBUG: Detected spaced header '{text}' matching '{self.SPACELESS_HEADERS[spaceless_clean]}'")
                    score += 3
                
                # B. Partial Keyword Match
                elif any(h in clean for h in self.HEADER_PATTERNS):
                    score += 1
                else:
                    if target_size is None and target_is_bold is None and target_is_upper is None:
                        continue

                # C. Visual Prominence
                if line["size"] > body_size + 1: score += 2
                if line["is_bold"]: score += 1
                if line["is_upper"]: score += 1

                # 3. DECISION LOGIC
                is_header = False
                if score >= 3:
                    is_header = True

                # Pass 1 Logic
                if target_size is None:
                    if is_header and text not in [h["text"] for h in detected_headers]:
                        # print("Detected Header (Pass 1):", text)
                        detected_headers.append(line)
                
                # Pass 2 Logic
                else:
                    is_final_header = False
                    size = round(line["size"], 1)
                    
                    if target_size is not None:
                        size_match = abs(size - target_size) <= 0.5
                        bold_match = (line["is_bold"] == target_is_bold)
                        upper_match = (line["is_upper"] == target_is_upper)
                        font_match = (line["font"] == target_font_name)

                        if size_match and bold_match and upper_match and font_match:
                            is_final_header = True
                        
                        elif spaceless_clean in self.SPACELESS_HEADERS:
                             if size_match: is_final_header = True
                        
                        if is_final_header and text not in [h["text"] for h in final_headers]:
                            print("Final Header Detected:", text)
                            final_headers.append(line)

            if final_headers:
                avg_header_block_height = sum(h["block_height"] for h in final_headers) / len(final_headers)
                return final_headers, body_size, avg_header_block_height

            if detected_headers:
                detected_sizes = [round(h["size"], 1) for h in detected_headers]
                target_size = Counter(detected_sizes).most_common(1)[0][0]
                target_is_bold = Counter([h["is_bold"] for h in detected_headers]).most_common(1)[0][0]
                target_is_upper = Counter([h["is_upper"] for h in detected_headers]).most_common(1)[0][0]
                target_font_name = Counter([h["font"] for h in detected_headers]).most_common(1)[0][0]
            else:
                break
        
        avg_header_block_height = sum(h["block_height"] for h in detected_headers) / len(detected_headers) if detected_headers else 0
        return detected_headers, body_size, avg_header_block_height