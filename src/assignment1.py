"""Assignment 1: data understanding, cleaning and integration.

Reads data/ProjectData/* and data/additional_truths.arff and writes the cleaned
tables to data/clean/*.csv (booleans as 0/1, missing values as empty fields,
dates as YYYY-MM-DD HH:MM:SS.ffffff).
All timestamps are US Eastern time (America/New_York): post times are decoded from the
Truth Social id, CR events and quotes take the time of their post.
Unknown authors are -1, with a matching row in users.csv (unknown member).
External lists live in data/external (us_states.csv, calendar.csv).
"""
import html
import re
from pathlib import Path
from urllib.parse import unquote

import arff
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
RAW, OUT = DATA / "ProjectData", DATA / "clean"
UNKNOWN = -1  # unknown author (unknown member of the user dimension)
EASTERN_TIME = "America/New_York"  # single clock for all timestamps
ARFF_SCRAPED_AT = pd.Timestamp("2026-09-24")  # retrieval date given

EXTERNAL_DATA = DATA / "external"  # external data

# state name (lower case) -> code; bare "Washington" is left out: mostly D.C. or George Washington
US_STATES = dict(pd.read_csv(EXTERNAL_DATA / "us_states.csv").values)
STATE_RE = re.compile(r"\b(" + "|".join(US_STATES) + r")\b", re.I)

# well-known dates (from Wikipedia), used to tag posts written around them
CALENDAR = pd.read_csv(EXTERNAL_DATA / "calendar.csv", parse_dates=["date"])
EVENT_WINDOW = 7  # days before/after an event that count as "around" it

# Unicode emoji (for the ARFF file)
EMOJI = "[\U0001F300-\U0001FAFF\u2600-\u27BF]"


def flag(s):
    return s.astype(str).map({"t": 1, "f": 0}).astype("Int8")


def fix_mojibake(s):
    # UTF-8 bytes stored as single characters ("’" -> "â\x80\x99"): re-join them
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeError, AttributeError):
        return s


def clean_text(s):
    # Fix empty texts and broken characters
    s = s.fillna("").map(fix_mojibake)
    # Clean leftover HTML tags
    s = s.str.replace(r"</?(?!emoji:)[a-z][^>]*>", " ", regex=True)
    return s.map(html.unescape)


def remap(ids, mapping):
    return pd.Series([mapping.get(i, i) for i in ids], index=ids.index, dtype=ids.dtype)


# ---------------------------------------------------------------- users
def clean_users():
    u = pd.read_xml(RAW / "users.xml", dtype={"username": str, "timestamp_user_creation": str})

    # Check and tag users that are placeholders
    placeholder = u.follower_count.eq(-1)
    u["is_placeholder"] = placeholder.astype("Int8")
    # Correct placeholders ts and cast
    created = pd.to_datetime(u.timestamp_user_creation.replace("-1", None))
    u["timestamp_user_creation"] = created.where(created >= "2020-01-01")
    # Cast correctly data for users that are not placeholders
    for c in ["follower_count", "following_count"]:
        u[c] = u[c].where(~placeholder).astype("Int64")
    for c in ["finished_follower_scrape", "finished_following_scrape", "finished_truth_scrape"]:
        u[c] = flag(u[c])
    no_name = u.username.eq("-1")
    u.loc[no_name, ["username", "profile_url"]] = pd.NA
    
    return u


# ---------------------------------------------------------------- truths
def load_truths():
    t = pd.read_csv(RAW / "truths.csv", dtype={"external_id": str}, keep_default_na=False, na_values=[""], low_memory=False)
    t = t.drop_duplicates()
    # same id, conflicting content: keep the copy that has a ReTruth target
    t = t.sort_values("truth_retruthed", ascending=False).drop_duplicates("id")

    # Some rows have shifted values (username->external_id;truth_social_id->url)
    shifted = ~t.external_id.str.fullmatch(r"\d+") | t.url.str.fullmatch(r"\d+", na=False)
    t.loc[shifted, "external_id"] = t.loc[shifted, "url"].where(t.loc[shifted, "url"].str.fullmatch(r"\d+"))
    t.loc[shifted, "url"] = pd.NA

    # Cast timestamps
    t["timestamp"] = pd.to_datetime(t.timestamp, format="mixed")
    t["time_scraped"] = pd.to_datetime(t.time_scraped, format="mixed")
    # Tag when rows were scraped based on scraped timestamp
    t["source"] = np.where(t.time_scraped.dt.year == 2024, "crawl_2024", "crawl_2022")
    # Binarize flags
    t["is_retruth"], t["is_reply"] = flag(t.is_retruth), flag(t.is_reply)
    # truth_retruthed is fixed, many were wrong
    rt = t.truth_retruthed
    valid = t.is_retruth.eq(1) & rt.gt(0) & rt.ne(t.id)
    t["truth_retruthed"] = rt.where(valid).astype("Int64")
    
    t["author"] = t.author.astype("Int64")
    
    return t


def load_arff():
    with open(DATA / "additional_truths.arff", encoding="utf-8") as f:
        raw = re.sub(r"\\x([0-9a-fA-F]{2})", r"\\u00\1", f.read())  # fix broken formatting
    d = arff.loads(raw)
    a = pd.DataFrame(d["data"], columns=[c[0] for c in d["attributes"]])

    a["id"] = a.external_id.astype("int64")  # = Truth Social id; liac-arff rounds the float id column
    # Cast columns to correct types
    a["timestamp"] = pd.to_datetime(a.timestamp)
    a["time_scraped"] = ARFF_SCRAPED_AT
    for c in ["reply_count", "retruth_count", "like_count", "author"]:
        a[c] = a[c].astype("Int64")
    # Create missing columns wrt truths file
    a["is_retruth"] = a.text.str.startswith("RT @").astype("Int8")
    a["is_reply"] = pd.array([0] * len(a), dtype="Int8")
    a["truth_retruthed"] = pd.array([pd.NA] * len(a), dtype="Int64")
    a["source"] = "trump_archive"
    
    return a


def integrate(t, a, users):
    t = pd.concat([t, a], ignore_index=True)
    t["text"] = clean_text(t.text)
    t["author"] = t.author.fillna(UNKNOWN).astype("int64")

    # some posts appear multiple times, due to the scraping
    key = ["external_id", "author"]
    rows = t[t.external_id.notna()].sort_values(["time_scraped", "id"])
    kept_id = rows.groupby(key).id.transform("last")  # id of the latest copy to keep
    copy = rows.id != kept_id  # older copies, to drop
    id_map = dict(zip(rows.id[copy], kept_id[copy]))  # dropped copy -> kept copy
    t = t[~t.id.isin(rows.id[copy])].copy()
    t["truth_retruthed"] = remap(t.truth_retruthed, id_map) # remaps retruths that may map to an older copy

    # authors missing from users.xml become placeholder users
    missing = sorted(set(t.author) - set(users.id_user) | {UNKNOWN})
    users = pd.concat([users, pd.DataFrame({"id_user": missing, "is_placeholder": 1})], ignore_index=True)
    users.loc[users.id_user.eq(UNKNOWN), "username"] = "(unknown)"
    users["id_user"] = users.id_user.astype("int64")
    users["is_placeholder"] = users.is_placeholder.astype("Int8")
    
    return t, id_map, users


def fix_timestamps(t):
    ok = t.external_id.str.fullmatch(r"\d{15,19}", na=False)  # one post has a wrong id and breaks the logic
    ms = pd.Series([int(x) >> 16 for x in t.external_id[ok]], index=t.index[ok])
    t.loc[ok, "timestamp"] = pd.to_datetime(ms, unit="ms", utc=True).dt.tz_convert(EASTERN_TIME).dt.tz_localize(None)
    return t


def derive_features(t, users):
    # Elements are counted in the text to create features
    txt = t.text.str.replace(r"<emoji: [^>]*>", " ", regex=True)
    t["n_emojis"] = t.text.str.count(r"<emoji: ") + txt.str.count(EMOJI)
    t["n_urls"] = txt.str.count(r"https?://\S+")
    txt = txt.str.replace(r"https?://\S+", " ", regex=True)
    t["n_hashtags"] = txt.str.count(r"#\w+")
    t["n_mentions"] = txt.str.count(r"@\w+")
    t["n_words"] = txt.str.split().str.len()
    
    letters = txt.str.count(r"[A-Za-z]")
    t["caps_ratio"] = (txt.str.count(r"[A-Z]") / letters).where(letters >= 20).round(3)
    t["us_states"] = txt.str.findall(STATE_RE).map(
        lambda m: ";".join(sorted({US_STATES[s.lower()] for s in m})) or pd.NA)

    # author of the reposted content: the author of the target post, or else the "RT @user"
    # at the start of the text (arff).
    by_handle = dict(zip(users.username.str.lower(), users.id_user))

    def rt_author(text):
        h = re.match(r"RT @(\w+)", text)
        h = h.group(1).lower() if h else ""
        for k in range(len(h), 2, -1):
            if h[:k] in by_handle:
                return by_handle[h[:k]]
        return pd.NA

    author_of = dict(zip(t.id, t.author))
    t["retruthed_author"] = pd.array([author_of.get(i) if pd.notna(i) else None for i in t.truth_retruthed], dtype="Int64")
    t["retruthed_author"] = t.retruthed_author.fillna(t.text.map(rt_author).astype("Int64"))

    # nearest calendar event within EVENT_WINDOW days (days_from_event < 0 = before it)
    diff = (t.timestamp.dt.normalize().values[:, None] - CALENDAR.date.values[None, :]) / np.timedelta64(1, "D")
    nearest = np.abs(diff).argmin(axis=1)
    days = pd.Series(diff[np.arange(len(t)), nearest], index=t.index)
    near = days.abs() <= EVENT_WINDOW
    t["calendar_event"] = pd.Series(CALENDAR.event.values[nearest], index=t.index).where(near)
    t["days_from_event"] = days.where(near).astype("Int64")
    
    return t


# ---------------------------------------------------------------- satellite tables
def clean_links(name, id_col, drop_col, truths, id_map):
    d = pd.read_json(RAW / f"{name}.json").drop(columns=drop_col)
    d["truth_id"] = remap(d.truth_id, id_map) 
    d = d.drop_duplicates([id_col, "truth_id"])
    return d[d.truth_id.isin(truths.id)].copy()


def clean_satellites(truths, users, id_map):
    # Media cleaning
    m = clean_links("media", "media_id", "id_media", truths, id_map)
    m = m[m.media_url.str.match(r"https?://\S+$")].copy()
    m["media_type"] = m.media_url.str.extract(r"\.(\w+)$")[0].str.lower().replace("jpeg", "jpg")

    # Hashtag cleaning
    h = clean_links("hashtags", "hashtag_id", "id_hashtag", truths, id_map)
    h["hashtag"] = h.hashtag.map(unquote).str.lower()
    h["first_seen"] = pd.to_datetime(h.first_seen)
    tag = h.groupby("hashtag")
    h["hashtag_id"] = tag.hashtag_id.transform("min")
    h["first_seen"] = tag.first_seen.transform("min")
    h = h.drop_duplicates(["hashtag_id", "truth_id"])

    # External URL cleaning
    x = clean_links("external_urls", "url_id", "id_ext_url", truths, id_map)
    x = x[x.url.str.match(r"https?://")].copy()
    x["domain"] = x.url.str.extract(r"https?://(?:www\.)?([^/:?#]+)")[0].str.lower()

    # Follow cleaning
    f = pd.read_json(RAW / "follows.json").drop_duplicates()
    f = f[f.follower.isin(users.id_user) & f.followed.isin(users.id_user)]

    # Quote cleaning
    q = pd.read_json(RAW / "quotes.json")
    q["quoting_truth"] = remap(q.quoting_truth, id_map)
    q = q.drop_duplicates(["quoting_truth", "quoted_truth_external_id"])  # two copies of a post, now one id
    q = q[q.quoting_truth.isin(truths.id)].copy()  # drop orphans
    q["timestamp"] = q.quoting_truth.map(truths.set_index("id").timestamp)
    # Recover original quoted post
    originals = truths[truths.is_retruth.eq(0) & truths.external_id.notna()]
    by_post = dict(zip(zip(originals.external_id, originals.author), originals.id))
    q["quoted_truth_id"] = pd.array([by_post.get((str(e), a)) for e, a in zip(q.quoted_truth_external_id, q.quoted_user)], dtype="Int64")
    
    return {"media": m, "hashtags": h, "external_urls": x, "follows": f, "quotes": q}


def clean_events(truths, id_map):
    e = pd.read_xml(RAW / "subsample_events.xml").drop(columns="index")
    e["timestamp"] = pd.to_datetime(e.timestamp, format="mixed").dt.floor("us")
    e["truth_id"] = remap(e.truth_id, id_map)
    e = e.drop_duplicates("event_id")
    post = truths.set_index("id")
    # Convert all to correct timestamp timezone
    utc = e.event_type.ne("CR") & e.truth_id.map(post.source).isin(["crawl_2024", "trump_archive"])
    e.loc[utc, "timestamp"] = (e.loc[utc, "timestamp"].dt.tz_localize("UTC").dt.tz_convert(EASTERN_TIME).dt.tz_localize(None))
    cr = e.event_type.eq("CR")
    e.loc[cr, "timestamp"] = e.loc[cr, "truth_id"].map(post.timestamp)

    return e


def main():
    users = clean_users()
    truths, id_map, users = integrate(load_truths(), load_arff(), users)
    truths = derive_features(fix_timestamps(truths), users)
    tables = {"users": users, "truths": truths, **clean_satellites(truths, users, id_map), "events": clean_events(truths, id_map), "truth_id_map": pd.DataFrame({"dropped_id": list(id_map), "kept_id": list(id_map.values())})}
    OUT.mkdir(exist_ok=True)
    for name, df in tables.items():
        df.to_csv(OUT / f"{name}.csv", index=False, date_format="%Y-%m-%d %H:%M:%S.%f")
    print(f"wrote {len(tables)} tables to {OUT}")


if __name__ == "__main__":
    main()
