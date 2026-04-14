import pandas as pd
import re


def parse_range(val):
    """
    Extract numeric range from text like:
    '0.01–1 ha' → (0.01, 1)
    """
    if pd.isna(val):
        return None

    nums=list(map(float, re.findall(r'\d+\.?\d*', str(val))))

    if not nums:
        return None

    return min(nums), max(nums)


def extract_depth_range(text):
    """
    Extract ONLY water depth (ignore height)
    Example:
    'Height: 3–6 m; Upstream depth: 0.5–3 m'
    → (0.5, 3)
    """
    if pd.isna(text):
        return None

    text=text.lower()

    #triess to find depth onlyu
    match=re.search(r'depth[^0-9]*(\d+\.?\d*)\D+(\d+\.?\d*)', text)

    if match:
        return float(match.group(1)), float(match.group(2))

    #fallback
    nums=list(map(float, re.findall(r'\d+\.?\d*', text)))
    if nums:
        return min(nums), max(nums)

    return None


def extract_slope_range(text):
    """
    Handles:
    '0–2%' → (0,2)
    '1:1.5 to 1:2' → ignore (not useful for site slope)
    """
    if pd.isna(text):
        return None

    text=text.lower()

    # only consider % slope
    if "%" in text:
        nums=list(map(float, re.findall(r'\d+\.?\d*', text)))
        if nums:
            return min(nums), max(nums)

    return None




class FeatureMatcher:

    def __init__(self, csv_path):
        self.df = pd.read_csv(csv_path)

    def match_score(self, site, row):

        score=0
        total=0
        reasons=[]
        issues=[]

        #area val
        area_range=parse_range(row["Area"])

        if area_range and site.get("area") is not None:
            total+=1
            if area_range[0] <= site["area"]<=area_range[1]:
                score+=1
                reasons.append("area fits")
            else:
                issues.append("area mismatch")

        #depth val
        depth_range=extract_depth_range(row["Height / Depth"])

        if depth_range and site.get("depth") is not None:
            total+=1
            if depth_range[0]<=site["depth"]<=depth_range[1]:
                score+=1
                reasons.append("depth fits")
            else:
                issues.append("depth mismatch")

        #slope val
        slope_range=extract_slope_range(row["Slope"])

        if slope_range and site.get("slope") is not None:
            total+=1
            if slope_range[0]<=site["slope"]<=slope_range[1]:
                score+=1
                reasons.append("slope fits")
            else:
                issues.append("slope mismatch")

        confidence=(score/total*100) if total else 0

        return score, confidence, reasons, issues

#recommneds water struct
    def recommend(self, site):

        results=[]

        for _, row in self.df.iterrows():

            score, confidence, reasons, issues=self.match_score(site, row)

            results.append({
                "type": row["Body Type"],
                "score": score,
                "confidence": confidence,
                "reasons": reasons,
                "issues": issues
            })

        results.sort(key=lambda x: x["confidence"], reverse=True)

        return results[:5]


    def check_suitability(self, site, body_type):

        for _, row in self.df.iterrows():

            if row["Body Type"].lower()==body_type.lower():

                score, confidence, reasons, issues=self.match_score(site, row)

             
                suitable=(
                    "area fits" in reasons and
                    "depth fits" in reasons
                )

                return {
                    "type": body_type,
                    "confidence": confidence,
                    "reasons": reasons,
                    "issues": issues,
                    "suitable": suitable
                }

        return None