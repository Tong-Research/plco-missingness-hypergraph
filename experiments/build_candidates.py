"""Build candidate matrices (X with NaN = missing, binary y, cols) into ~/.cache/phd-matrices for screening.

    --which higgs   OpenML 45550 (ATLAS Higgs ML challenge, 818k): jet-dependent variables are undefined
                    (-999) when the event has fewer jets -- missing means 'does not apply'. y = signal.
    --which acs     folktables ACS PUMS 2018 person file, raw columns kept with their skip-logic blanks
                    (work hours, occupation, commute apply only to workers, etc.). y = public coverage.
"""
import argparse, pathlib
import numpy as np, pandas as pd
CACHE = pathlib.Path.home() / ".cache/phd-matrices"

def higgs():
    from sklearn.datasets import fetch_openml
    d = fetch_openml(data_id=45550, as_frame=True, parser="auto")
    df = d.frame.copy()
    ycol = [c for c in df.columns if c.lower() in ("label", "class", "target")]
    ycol = ycol[0] if ycol else d.target.name
    y = (df[ycol].astype(str).str.lower().isin(["s", "1", "signal", "true"])).astype(int).to_numpy()
    X = df.drop(columns=[ycol] + [c for c in df.columns if c.lower() in ("eventid", "weight", "kaggleset", "kaggleweight")])
    X = X.apply(pd.to_numeric, errors="coerce"); X = X.mask(X <= -998.0)   # -999 = undefined
    return X.to_numpy(float), y, list(X.columns)

def porto():
    """OpenML 42742 (Porto Seguro safe-driver, 595k, 58 features): -1 marks missing in the original release;
    product-block variables (ps_car_*, ps_reg_*, ps_ind_*) are missing for whole segments of policies."""
    from sklearn.datasets import fetch_openml
    d = fetch_openml(data_id=42742, as_frame=True, parser="auto")
    df = d.frame.copy(); ycol = d.target.name
    y = pd.to_numeric(df[ycol], errors="coerce").fillna(0).astype(int).to_numpy()
    X = df.drop(columns=[ycol] + [c for c in df.columns if c.lower() == "id"]).apply(pd.to_numeric, errors="coerce")
    X = X.mask(X == -1)
    return X.to_numpy(float), y, list(X.columns)

def acs():
    from folktables import ACSDataSource
    src = ACSDataSource(survey_year="2018", horizon="1-Year", survey="person", root_dir=str(CACHE / "acs_raw"))
    df = src.get_data(states=["CA", "TX", "NY", "FL", "PA", "IL", "OH", "GA", "NC", "MI"], download=True)
    keep = ["AGEP", "SCHL", "MAR", "SEX", "RAC1P", "DIS", "CIT", "MIG", "MIL", "ANC", "NATIVITY", "DEAR", "DEYE", "DREM",
            "ESR", "COW", "WKHP", "WKW", "OCCP", "INDP", "JWMNP", "JWTR", "PINCP", "WAGP", "SEMP", "INTP", "RETP", "SSP",
            "PAP", "OIP", "FER", "ENG", "LANX", "GCL", "HINS1", "HINS2", "HINS3", "HINS4", "ESP", "MSP", "NWAB", "NWAV", "NWLA", "NWLK", "NWRE"]
    keep = [c for c in keep if c in df.columns]
    df = df[df["AGEP"] >= 16]
    y = (df["PUBCOV"] == 1).astype(int).to_numpy()
    X = df[[c for c in keep if c != "PUBCOV"]].apply(pd.to_numeric, errors="coerce")
    return X.to_numpy(float), y, list(X.columns)

def acs_income():
    """ACS 2018 person file, ten states, age >= 16: y = total personal income > 50,000; every income and
    earnings column dropped (PINCP, WAGP, SEMP, INTP, RETP, SSP, PAP, OIP, SSIP) and the insurance columns
    that leaked the previous target (HINS*, PUBCOV) dropped too. Skip-logic blanks kept (work hours,
    occupation, industry, commute apply only to workers; fertility to women 15-50; etc.)."""
    from folktables import ACSDataSource
    src = ACSDataSource(survey_year="2018", horizon="1-Year", survey="person", root_dir=str(CACHE / "acs_raw"))
    df = src.get_data(states=["CA", "TX", "NY", "FL", "PA", "IL", "OH", "GA", "NC", "MI"], download=True)
    keep = ["AGEP", "SCHL", "MAR", "SEX", "RAC1P", "DIS", "CIT", "MIG", "MIL", "ANC", "NATIVITY", "DEAR", "DEYE", "DREM",
            "ESR", "COW", "WKHP", "WKW", "OCCP", "INDP", "JWMNP", "JWTR", "FER", "ENG", "LANX", "GCL", "ESP", "MSP",
            "NWAB", "NWAV", "NWLA", "NWLK", "NWRE", "SCH", "SCHG", "FOD1P", "DRAT", "DRATX", "RELP", "POWSP", "WRK", "YOEP", "DECADE"]
    keep = [c for c in keep if c in df.columns]
    df = df[df["AGEP"] >= 16]
    y = (pd.to_numeric(df["PINCP"], errors="coerce").fillna(0) > 50_000).astype(int).to_numpy()
    X = df[keep].apply(pd.to_numeric, errors="coerce")
    return X.to_numpy(float), y, list(X.columns)

AIRBNB = {"london": "https://data.insideairbnb.com/united-kingdom/england/london/2026-06-19/data/listings.csv.gz",
          "los-angeles": "https://data.insideairbnb.com/united-states/ca/los-angeles/2026-06-15/data/listings.csv.gz",
          "new-york-city": "https://data.insideairbnb.com/united-states/ny/new-york-city/2026-08-10/data/listings.csv.gz",
          "paris": "https://data.insideairbnb.com/france/ile-de-france/paris/2026-06-16/data/listings.csv.gz",
          "sydney": "https://data.insideairbnb.com/australia/nsw/sydney/2026-06-16/data/listings.csv.gz"}
AIRBNB_KEEP = ["host_response_rate", "host_acceptance_rate", "host_is_superhost", "host_listings_count", "host_total_listings_count",
               "host_has_profile_pic", "host_identity_verified", "latitude", "longitude", "accommodates", "bathrooms", "bedrooms", "beds",
               "minimum_nights", "maximum_nights", "availability_30", "availability_60", "availability_90", "availability_365",
               "number_of_reviews", "number_of_reviews_ltm", "number_of_reviews_l30d", "review_scores_rating", "review_scores_accuracy",
               "review_scores_cleanliness", "review_scores_checkin", "review_scores_communication", "review_scores_location",
               "review_scores_value", "instant_bookable", "calculated_host_listings_count", "reviews_per_month"]

def airbnb():
    """SHOWCASE.md item A: five Inside Airbnb city snapshots pooled; y = price above the city median."""
    import io, urllib.request
    frames = []
    for i, (city, url) in enumerate(AIRBNB.items()):
        raw = urllib.request.urlopen(url, timeout=300).read(); df = pd.read_csv(io.BytesIO(raw), compression="gzip", low_memory=False)
        price = pd.to_numeric(df["price"].astype(str).str.replace(r"[\$,]", "", regex=True), errors="coerce"); df = df[price.notna() & (price > 0)]; price = price[df.index]
        X = df[[c for c in AIRBNB_KEEP if c in df.columns]].copy()
        for c in ["host_response_rate", "host_acceptance_rate"]:
            if c in X: X[c] = pd.to_numeric(X[c].astype(str).str.rstrip("%"), errors="coerce")
        for c in ["host_is_superhost", "host_has_profile_pic", "host_identity_verified", "instant_bookable"]:
            if c in X: X[c] = X[c].map({"t": 1.0, "f": 0.0})
        X = X.apply(pd.to_numeric, errors="coerce"); X["city"] = float(i)
        X["y"] = (price > price.median()).astype(int).to_numpy(); frames.append(X); print(f"  {city}: {len(X):,} listings", flush=True)
    A = pd.concat(frames, ignore_index=True); y = A.pop("y").to_numpy(); return A.to_numpy(float), y, list(A.columns)

def realestate():
    """SHOWCASE.md item B: OpenML 43631; y = price above the overall median; identifier-like columns dropped."""
    from sklearn.datasets import fetch_openml
    d = fetch_openml(data_id=43631, as_frame=True, parser="auto", target_column=None); df = d.frame
    pcol = [c for c in df.columns if c.lower() in ("price", "listprice", "list_price", "sold_price")]
    assert pcol, list(df.columns)[:40]
    price = pd.to_numeric(df[pcol[0]], errors="coerce"); df = df[price.notna() & (price > 0)]; price = price[df.index]
    X = df.drop(columns=pcol).apply(pd.to_numeric, errors="coerce"); X = X.loc[:, X.notna().any()]; X = X.loc[:, X.abs().max() <= 1e15]
    y = (price > price.median()).astype(int).to_numpy(); return X.to_numpy(float), y, list(X.columns)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--which", required=True); a = ap.parse_args()
    X, y, cols = {"higgs": higgs, "acs": acs, "porto": porto, "acs_income": acs_income, "airbnb": airbnb, "realestate": realestate}[a.which]()
    out = CACHE / f"cand_{a.which}.npz"; np.savez_compressed(out, X=X, y=y, cols=np.array(cols))
    M = np.isnan(X); print(f"  {a.which}: n {len(X):,} d {X.shape[1]} prev {y.mean():.3f} missing {M.mean():.1%} patterns {len({r.tobytes() for r in M}):,} -> {out}")

if __name__ == "__main__":
    main()
