from pydoc import doc
import pymupdf as fitz
def draw_section_boundaries(page, column_blocks, headers, color):
    """
    Groups blocks into sections based on headers and draws a box around the entire group.
    """
    if not column_blocks:
        return

    current_section_group = []

    for b in column_blocks:

        is_header = any(header["text"].lower() in b["full_text"].strip().lower() for header in headers)

        if is_header:
            if current_section_group:
                # Calculate the "Union" rectangle of all blocks in the group
                union_rect = fitz.Rect(current_section_group[0]["bbox"])
                for block in current_section_group[1:]:
                    union_rect |= fitz.Rect(block["bbox"]) # '|' is the union operator in PyMuPDF
                    union_rect += (1,1,1,1)  # Slightly expand the rectangle for better visibility

                page.draw_rect(union_rect, color=color, width=1.5)
                page.insert_text((union_rect.x0, union_rect.y0 - 2), f"Section: {current_section_group[0]['full_text'].strip().lower()}", color=color, fontsize=6)
            
            # Start a NEW section with this header block
            current_section_group = [b]
        else:
            # It's body text; add it to the currently running section
            current_section_group.append(b)

    # LAST section after the loop finishes
    if current_section_group:
        union_rect = fitz.Rect(current_section_group[0]["bbox"])
        for block in current_section_group[1:]:
            union_rect |= fitz.Rect(block["bbox"])
        page.draw_rect(union_rect, color=color, width=1.5)
        page.insert_text((union_rect.x0, union_rect.y0 - 2), f"Section: {current_section_group[0]['full_text'].strip().lower()}", color=color, fontsize=6)


def generate_layout_debug_pdf(doc_path, headings, body_size, avg_header_block_height):
    """
    Analyzes the layout of the first page of the PDF at 'doc_path'.
    Applies geometric logic to detect columns, headers, and body text.
    
    Returns:
        bytes: The binary data of the generated Debug PDF (for download/display).
    """
    
    # Open the document
    with fitz.open(doc_path) as doc:
        page = doc[0]  # Working on the first page

        # Colors (R, G, B)
        COLOR_HEADER = (1, 0, 0)      # Red
        COLOR_LEFT   = (0, 0, 1)      # Blue
        COLOR_RIGHT  = (0, 0.5, 0)    # Green
        COLOR_BODY   = (1, 0.5, 0)    # Orange
        COLOR_SPLIT  = (1, 0, 1)      # Magenta
        COLOR_HEADING = (0.5, 0, 0.5)  # Purple
        COLOR_SECTION_BOX = (0, 0.8, 0.8) # Cyan
        raw_dict = page.get_text("dict")
        text_blocks = []

        for b in raw_dict["blocks"]:
            if b["type"] != 0: continue
            block_text = ""
            for line in b["lines"]:
                for span in line["spans"]:
                    block_text += span["text"] + " "
                block_text += "\n"
            b["full_text"] = block_text
            text_blocks.append(b)

        if not text_blocks:
            print("No text found to debug.")
            return

        text_blocks.sort(key=lambda b: b["bbox"][1])
        
        header_gaps = []
        for i in range(1, len(text_blocks)):
            if any(header["text"] in text_blocks[i]["full_text"].strip() for header in headings):
                gap = text_blocks[i+1]["bbox"][1] - text_blocks[i]["bbox"][3]
                header_gaps.append(gap)
        avg_header_gap = sum(header_gaps) / len(header_gaps) if header_gaps else 0
        print(f"Avg Header Gap (Debug): {avg_header_gap}")

        # --- Find Split Logic (Copied from your function) ---
        found_split_y = None
        min_col_width = page.rect.width * 0.05
        
        for i, b1 in enumerate(text_blocks):
            if found_split_y is not None: break
            y1_top, y1_bottom = b1["bbox"][1], b1["bbox"][3]
            b1_width = b1["bbox"][2] - b1["bbox"][0]
            if b1_width < min_col_width: continue

            for b2 in text_blocks[i+1:]:
                y2_top = b2["bbox"][1]
                y2_bottom = b2["bbox"][3]
                if y2_top >= y1_bottom: break
                b2_width = b2["bbox"][2] - b2["bbox"][0]
                if b2_width < min_col_width: continue

                vertical_overlap = (y2_top < y1_bottom) and (y2_bottom > y1_top)
                horizontal_separation = (b1["bbox"][2] < b2["bbox"][0]) or (b2["bbox"][2] < b1["bbox"][0])
                
                if vertical_overlap and horizontal_separation:
                    found_split_y = min(y1_top, y2_top)
                    break

        # =========================================================================
        
        # 1. Draw Single Column (if no split found)
        if found_split_y is None:
            print("Debug: No split found - marking all as Body.")
            for b in text_blocks:
                page.draw_rect(b["bbox"], color=COLOR_BODY, width=1.5)
                page.insert_text((b["bbox"][0], b["bbox"][1]-2), "Body", color=COLOR_BODY, fontsize=8)

        # 2. Draw Two Column Layout
        else:
            print(f"Debug: Split found at {found_split_y}")
            split_threshold = found_split_y - 5
            
            header_blocks = []
            body_blocks = []

            # --- Initial Classification ---
            for i in range(len(text_blocks)):
                # Check if block is above split threshold OR straddles it significantly
                is_above_split = (text_blocks[i]["bbox"][3] <= split_threshold) or \
                                (text_blocks[i]["bbox"][1] < split_threshold and text_blocks[i]["bbox"][3] > split_threshold)
                
                if is_above_split:
                    is_heading_text = any(heading["text"] in text_blocks[i]["full_text"].strip() for heading in headings)
                    # Heuristic: If previous block was body, this might be body too
                    prev_was_body = (text_blocks[i-1] in body_blocks) if i > 0 else False
                    # Heuristic: Font size check
                    small_font = any(s["size"] <= body_size+2 for line in text_blocks[i]["lines"] for s in line["spans"])

                    if is_heading_text:
                        body_blocks.append(text_blocks[i]) 
                        pass 
                    elif prev_was_body:
                        body_blocks.append(text_blocks[i])
                    elif small_font:
                        body_blocks.append(text_blocks[i])
                    else:
                        header_blocks.append(text_blocks[i]) # This is likely Name/Title
                else:
                    body_blocks.append(text_blocks[i])
            
            # 3b. Process Header
            header_blocks.sort(key=lambda b: b["bbox"][1])
            header_text = "\n".join([b["full_text"].strip() for b in header_blocks])

            # -- Calculate Dynamic Center --
            dynamic_center = 0
            left_col = []
            right_col = []

            if body_blocks:
                body_x0_values = [b["bbox"][0] for b in body_blocks]
                dynamic_center = sum(body_x0_values) / len(body_x0_values)
                
                # Initial Geometric Split
                for b in body_blocks:
                    if b["bbox"][0] < dynamic_center:
                        left_col.append(b)
                    else:
                        right_col.append(b)

                # Sort columns internally by Y
                left_col.sort(key=lambda b: (b["bbox"][1]))
                right_col.sort(key=lambda b: (b["bbox"][1]))

                # 1. Left to Right: Collect items to move until a header is found
                to_move_to_right = []
                for b in left_col:
                    if any(header["text"] in b["full_text"].strip() for header in headings):
                        break 
                    # Your specific condition from the updated code
                    if not (b["bbox"][3] <= split_threshold or b["bbox"][1] < split_threshold and b["bbox"][3] > split_threshold):
                        to_move_to_right.append(b)
                
                for b in to_move_to_right:
                    if b in left_col: left_col.remove(b)
                    right_col.append(b) 

                # Right to Left: Collect items to move until a header is found
                to_move_to_left = []
                
                for i in range(len(right_col)):
                    normal_block = right_col[i]
                    if any(header["text"] == normal_block["full_text"].strip() for header in headings):
                        continue
                    else:
                        found_header = False
                        for j in range(i):
                            if any(header["text"] == right_col[j]["full_text"].strip() for header in headings):
                                header_block = right_col[j]
                                if header_block["bbox"][3] < normal_block["bbox"][1] and header_block["bbox"][0] <= (normal_block["bbox"][0] + 10) and header_block["bbox"][0] >= dynamic_center:
                                    found_header = True
                                    break
                        if not found_header and normal_block not in to_move_to_left:
                            to_move_to_left.append(normal_block)

                for b in to_move_to_left:
                    if b in right_col: right_col.remove(b)
                    left_col.append(b)

                # Sort columns internally
                left_col.sort(key=lambda b: (b["bbox"][1]))
                right_col.sort(key=lambda b: (b["bbox"][1]))
                
                if avg_header_block_height > 0 and avg_header_gap > 0:
                    print(avg_header_block_height + avg_header_gap)
                    gap_found = False
                    to_move_to_left = []
                    for i in range(len(right_col)-1):
                        normal_block = right_col[i]
                        if any(header["text"] in normal_block["full_text"].strip() for header in headings):
                            gap_found = False
                            continue
                        if i < len(right_col) - 1:
                            if right_col[i+1]["bbox"][1] - normal_block["bbox"][3] >= (avg_header_gap + avg_header_block_height + 5) and not gap_found and not any(header["text"] in right_col[i+1]["full_text"].strip() for header in headings):
                                print("Gap Found (Debug)", right_col[i+1]["bbox"][1] - normal_block["bbox"][3])
                                print("after this text:", normal_block["full_text"].strip())
                                gap_found = True
                        if gap_found:
                            to_move_to_left.append(right_col[i+1])
                    for b in to_move_to_left:
                        if b in right_col: right_col.remove(b)
                        left_col.append(b)

            # -- DRAWING COMMANDS --

            # A. Draw Header Blocks
            for b in header_blocks:
                page.draw_rect(b["bbox"], color=COLOR_HEADER, width=2)
                page.insert_text((b["bbox"][0], b["bbox"][1]-5), "HEADER", color=COLOR_HEADER, fontsize=10)      

            # B. Draw Left Column (Blue) - iterate the LIST, not geometry
            for b in left_col:
                if b["full_text"].strip() in [h["text"] for h in headings]:
                    page.draw_rect(b["bbox"], color=COLOR_HEADING, width=1.5)
                    page.insert_text((b["bbox"][0], b["bbox"][3]+5), "Header || Left", color=COLOR_HEADING, fontsize=6)
                else:
                    page.draw_rect(b["bbox"], color=COLOR_LEFT, width=1.5)
                    page.insert_text((b["bbox"][0], b["bbox"][1]-2), "Left", color=COLOR_LEFT, fontsize=6)

            # C. Draw Right Column (Green) - iterate the LIST, not geometry
            for b in right_col:
                if b["full_text"].strip() in [h["text"] for h in headings]:
                    page.draw_rect(b["bbox"], color=COLOR_HEADING, width=1.5)
                    page.insert_text((b["bbox"][0], b["bbox"][3]+5), "Header || Right", color=COLOR_HEADING, fontsize=6)
                else:
                    page.draw_rect(b["bbox"], color=COLOR_RIGHT, width=1.5)
                    page.insert_text((b["bbox"][0], b["bbox"][1]-2), "Right", color=COLOR_RIGHT, fontsize=6)

            # D. Draw Split Threshold Line
            page.draw_line((0, split_threshold), (page.rect.width, split_threshold), color=COLOR_SPLIT, width=2)
            page.insert_text((5, split_threshold - 5), f"Split Threshold: {split_threshold:.1f}", color=COLOR_SPLIT)

            # E. Draw Dynamic Center Line
            if body_blocks:
                page.draw_line((dynamic_center, split_threshold), (dynamic_center, page.rect.height), color=COLOR_LEFT, width=2)
                page.insert_text((dynamic_center + 5, split_threshold + 20), "Dynamic Center", color=COLOR_LEFT, fontsize=8)

            # F. Draw Section Boundaries for Left Column
            draw_section_boundaries(page, left_col, headings, COLOR_SECTION_BOX)
            # G. Draw Section Boundaries for Right Column
            draw_section_boundaries(page, right_col, headings, COLOR_SECTION_BOX)

        # Save to bytes
        pdf_bytes = doc.write()
        return pdf_bytes