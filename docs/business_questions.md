# Business questions

Requirements for the data warehouse, collected before the design so that the warehouse needs no
change after the database freeze on 11 December. Questions 1–8 are set by the assignments.
Questions 9–17 are the candidates for the free assignments (A12, A13, A19, A20, A21).

## Conventions

**Measures.** The fact is measureless, so every measure is an indicator over the events, like
`Passed` in the course's exams example:

- `Event` = 1 for every event
- `Post` = CASE WHEN EventType = 'CR' THEN 1 ELSE 0 END (a post being created; ReTruths are posts too)
- `Like` = CASE WHEN EventType = 'LI' THEN 1 ELSE 0 END
- `Reply` = CASE WHEN EventType = 'REP' THEN 1 ELSE 0 END
- `SizeKB` = size of a media file from its type: JPG 400, PNG 2,048, GIF 10,240 (1 MB = 1,024 KB)

**Dimension roles.**

- `Author` is the user who wrote the post the event refers to (User hierarchy).
- `Date` is the date of the event, and `PostDate` is the date the post was created (Date hierarchy).
  They differ: a like is dated a median of 59 days after its post.

**Original post.** A post that is not a ReTruth (IsRetruth = false).

## Mandatory questions

| # | Assignment | Business question | What it implies | Dimensions (attributes) | Measures | Metrics |
|---|---|---|---|---|---|---|
| 1 | A8 (SSIS) | Ratio between the number of posts released at night (8 pm–8 am) and during the day (8 am–8 pm), and the same ratio for the likes received by those posts, by author. | A user's posts are counted through their CR events. Likes are split by when the liked post was released, not by when the like was given, because the times of likes were generated. A user with no daytime posts, or no likes on daytime posts, has no score. | Author (UserID, Username)<br>Post (PostDayPart) | Post, Like | SUM(Post) at night / SUM(Post) by day<br>SUM(Like) at night / SUM(Like) by day |
| 2 | A9 (SSIS) | Ratio between the cumulative number of likes and the cumulative number of posts, ReTruths included, by post category, by month. | Cumulative means a running total from the first month up to the current one, within the category. A like counts in the month it was given, and a post in the month it was created. | Post (Category)<br>Date (Month, Year) | Like, Post | running SUM(Like) / running SUM(Post) |
| 3 | A10 (SSIS) | Ratio between the average number of likes per post of a category and the average number of likes per post of all the other categories together, by post category. | The average is likes divided by posts, so a post without likes counts as 0. The other categories are pooled: their likes divided by their posts, not the mean of their averages. | Post (Category) | Like, Post | (SUM(Like) / SUM(Post)) in the category ÷ (SUM(Like) / SUM(Post)) outside it |
| 4 | A11 (SSIS) | Percentage of trending posts and trending factor, by author, by post category; the same statistics for the posts that are ReTruths of Donald Trump, in a separate file. | Likes are counted per post. The average and the population standard deviation are taken over all of the author's posts. A post trends when its likes are at least one standard deviation above the average, and flops when they are at least one below. Trending percentage = trending posts / posts × 100. Trending factor = (trending − flopping) / (trending + flopping), left empty when both are 0. Edge cases: an author with one post has no standard deviation, and with a standard deviation of 0 no post trends or flops. The Trump file recomputes everything on the posts with RetruthedAuthor = Donald Trump. It misses the ReTruths whose original author is unknown, and since a ReTruth carries the likes of the post it reposts, it ranks the Trump posts each user chose to repost. | Author (UserID)<br>Post (TruthID, Category, RetruthedAuthor) | Like, Post | per post: SUM(Like)<br>per author: AVG and STDEVP of the per-post likes<br>COUNT of trending and of flopping posts |
| 5 | A15 (MDX) | Total number of events on each account's posts, and the overall total for all accounts, by month. | The account is the author of the post the event refers to, because the users who like, repost or reply were assigned at random. The overall total is the All member of Author. | Author (UserID, Username)<br>Date (Month, Year) | Event | SUM(Event) |
| 6 | A16 (MDX) | Average yearly media storage space, and the grand total over all years, counting a JPG as 400 KB, a PNG as 2 MB and a GIF as 10 MB. | The year is the year the post was created, taken from its CR event. The query counts a file once for each post that uses it; the report explains how to count each distinct file once instead (distinct media ids). Media were collected only by the 2022 crawl, so the yearly average covers a single year. The query relies on every post with media having its CR event in the full events table. | Date (Year)<br>EventType (Code = CR)<br>Media (MediaType, SizeKB), through the PostMedia bridge | SizeKB | SUM(SizeKB) by year<br>AVG over the years<br>grand total |
| 7 | A17 (MDX) | Percentage increase or decrease in the number of events compared with the previous year, by post category, by year. | The year is the year of the event. The first year has no previous year, so its change is empty. Most of the change reflects when the data was collected: in the subsample the events fall by about 93% from 2022 to 2023, because the 2022 crawl ends in October 2022. The report says so. | Post (Category)<br>Date (Year) | Event | (SUM(Event) in y − SUM(Event) in y−1) / SUM(Event) in y−1 × 100 |
| 8 | A18 (MDX) | Post categories whose number of likes in a season exceeds the average number of likes per category in the same season of the previous year, with the increase as a percentage, by season, by year. | Seasons are taken within the calendar year: winter is January, February and December, spring March to May, summer June to August, autumn September to November. A like counts in the season it was given. The reference is the average over all categories of the likes in the same season of the previous year. Increase = (likes − reference) / reference × 100. | Post (Category)<br>Date (Season, Year) | Like | SUM(Like) by category and season<br>AVG over the categories of SUM(Like) in the same season of y−1 |

## Free assignments

The free part needs three queries (A12 and A13 in SSIS, A19 in MDX) and two dashboards (A20, A21).
The specification asks A12 and A13 to build on the results of the previous queries, A12 to focus
on one or a few accounts with many followers, and A19 to be non-trivial.

There are two sets of candidates: questions 9–13 from the first round, and questions 14–17 from
the six proposals of the second round that survived the check below. The design supports all of
them, so the choice does not change the warehouse.

**Suggested choice.** A12 = 9, A13 = 14 (it builds on A11, while 10 builds on nothing),
A19 = 11 with 16 as a backup, A20 = 12, A21 = 13. The SSIS code is due with the freeze on
11 December, so A12 and A13 must be decided by then; A19 can be decided later.

### Second-round proposals checked against the data

| # | Proposal | What the data shows | Verdict |
|---|---|---|---|
| a | For each post category, the ratio between trending posts containing a hashtag and trending posts without a hashtag. | The plain ratio mostly measures how common hashtags are in each category: it is 4.97 in "Trump and MAGA", where the hashtag-chain posts are, and 0 in "Link only". Nearly every post of the 2024 crawl has a hashtag (96%, against 9% in the 2022 crawl and 2% in the archive), so mixing sources compares crawls rather than posts. | Keep, reworded as a ratio of trending rates on the 2022 crawl (question 14). |
| b | For each user with at least 100,000 followers, the post id, number of likes, number of mentions and day of posting of their most popular post. | 150 accounts with posts have at least 100,000 followers. For 4 of them the most liked post is a ReTruth, which carries the likes of the post it reposts. One account has two posts tied for first. | Keep, on original posts only (question 15). |
| c | For each year and post category, the number of posts by Trump. | Correct, and the design already answers it, but it is a single grouping, and the A21 dashboard already shows Trump's category shares by month. | Fold into A21. |
| d | For each year and month, the most used media_id. | Media exist only for February–November 2022. In every month the top file is the image of one original post repeated by its ReTruths (322 times in April 2022). February and November have two tied files, and September has four (the four images of one post). | Keep (question 16). |
| e | The user_id and follower count of each user with more reposts than posts in 2026. | In 2026 the only posts are Trump's archive: 271 ReTruths out of 5,794 posts, so the answer is empty. Counted as RET events, the reposters are random users, and 2,089 of them qualify in the subsample alone. The 2024 crawl has no ReTruths, so only 2022 can produce a real answer. | Drop. |
| f | The quoting post id, the quoted post id and the difference between their likes, when the quoting post has more likes than the quoted post. | 9,593 quotes, all from the 2022 crawl. The quoted post is in the dataset for 2,179 of them, and the quote has more likes in 173 cases. 583 of the 2,179 are accounts quoting themselves. Each post quotes at most one post. | Keep as an SSIS alternative (question 17). |

### Candidate questions

| # | Assignment | Business question | What it implies | Dimensions (attributes) | Measures | Metrics |
|---|---|---|---|---|---|---|
| 9 | A12 (SSIS) | Share of each post category in the account's original posts, and number of likes per original post in that category, by account, for the six most followed accounts with at least 100 original posts. | It shows whether these accounts post most about the topics that earn them the most likes, building on A10. ReTruths are left out, because a ReTruth carries the likes of the post it reposts. "Most followed" uses the follower count at scrape time, which is a single snapshot. The rule selects Donald Trump, Donald Trump Jr., Dan Bongino, Babylon Bee, Newsmax and Dinesh D'Souza. | Author (UserID, Username, FollowerCount)<br>Post (Category, IsRetruth) | Post, Like | SUM(Post) in the category / SUM(Post) of the account<br>SUM(Like) / SUM(Post) in the category |
| 10 | A13 (SSIS) | Number of replies per like, by post category. | A high ratio marks topics that start discussion rather than collect approval. Replies and likes are counted on the same posts. | Post (Category) | Reply, Like | SUM(Reply) / SUM(Like) |
| 11 | A19 (MDX) | Percentage change in the number of posts in the 7 days after a political event compared with the 7 days before, by calendar event, by post category, with the categories that grew most for each event. | It uses the seven dates of the external calendar from A1. Days −7 to −1 are before the event and days 1 to 7 after it; the event day itself is left out. Posts are counted on the date they were created. The assassination attempt (13 July 2024) and Biden's withdrawal (21 July) are 8 days apart, so their windows overlap, and A1 gives each day to the nearest event: 14–17 July go to the attempt and 18–20 July to the withdrawal. The attempt therefore has only 4 days after it and the withdrawal only 3 days before it, so the query compares posts per day instead of totals. The MDX is non-trivial because it needs two date ranges relative to each event and a ranking within each event. | Date (Day, CalendarEvent, DaysFromEvent)<br>Post (Category) | Post | (posts per day after − posts per day before) / posts per day before × 100, where posts per day = SUM(Post) / number of days on that side<br>TOPCOUNT within each event |
| 12 | A20 (dashboard) | Number of posts, and number of likes received by those posts, by day, by post category, from 1 to 15 August 2022, around the FBI search of Mar-a-Lago on 8 August. | The reaction is measured through the posts written around the event and the likes they received, not through when the likes were given. 47,276 posts fall in this window. The dashboard highlights "FBI, courts and trials" and compares the days after the search with the days before. | PostDate (Day, CalendarEvent, DaysFromEvent)<br>Post (Category) | Post, Like | SUM(Post) and SUM(Like) by day and category |
| 13 | A21 (dashboard) | Number of posts, share of ReTruths, share of posts released at night, number of likes per post and share of each post category, by month, for Donald Trump, across 2022, the 2024 campaign and 2025–2026. | Trump is the only account covered continuously from 2022 to 2026, through the archive. Posts are placed in the month they were created, and likes in the month of the post they went to. The 2024 campaign dates in the calendar (conviction, debate, assassination attempt, Biden's withdrawal) mark the timeline. Proposal c is the category part of this dashboard. | Author (UserID = Donald Trump)<br>PostDate (Month, Year, CalendarEvent)<br>Post (Category, IsRetruth, PostDayPart) | Post, Like | SUM(Post)<br>SUM(Like) / SUM(Post)<br>shares of SUM(Post) |
| 14 | A13 (SSIS) | Ratio between the share of trending posts among the posts with at least one hashtag and the share of trending posts among the posts without hashtags, by post category, for the 2022 crawl. | Trending is defined as in A11: likes at least one standard deviation above the author's average over all of their posts. Comparing rates instead of counts removes the effect of how common hashtags are in each category. The question is limited to the 2022 crawl because nearly every 2024-crawl post has a hashtag. Hashtags are counted from the text (n_hashtags), because the hashtags table covers only the 2022 crawl. In the 2022 crawl, posts with a hashtag trend 1.34 times as often as posts without; by category the ratio goes from 0.82 to 1.73. "Link only" and "No text" have no hashtag posts, so they have no ratio. The original count ratio uses the same data. | Author (UserID)<br>Post (TruthID, Category, NHashtags, Source) | Like, Post | per post: SUM(Like)<br>per author: AVG and STDEVP of the per-post likes<br>(trending with hashtag / posts with hashtag) ÷ (trending without / posts without) |
| 15 | A12 (SSIS) | Most liked original post, with its number of likes, number of mentions, post category and day of posting, by account, for the accounts with at least 100,000 followers. | Only original posts are compared, because a ReTruth carries the likes of the post it reposts. Tied posts are all returned. The specification asks A12 for one or a few accounts, and 150 is many: a threshold of 1,000,000 followers leaves 11 accounts, and 500,000 leaves 37. The query becomes analytical if the top post's likes are also divided by the account's average likes per post, which shows how far the hit stands out (it builds on A11). The day is the day the post was created. | Author (UserID, Username, FollowerCount)<br>Post (TruthID, Category, NMentions, IsRetruth)<br>PostDate (Day) | Like | per post: SUM(Like)<br>per account: MAX of the per-post likes, and the post that reaches it |
| 16 | A19 (MDX) | Most used media file, with its number of uses, by month. | A use is a post that contains the file, counted through its CR event and the PostMedia bridge, the same way A16 counts. It builds on A16: in every month the top file is the image of one original post repeated by its ReTruths, because a ReTruth copies the original's media, and 58% of the media rows sit on ReTruths. This explains the gap between A16's two ways of counting. Because of ties, the query returns every file with the top count of the month, not TOPCOUNT(…, 1). ReTruth rows carry the original post's date, so all the uses of a reposted image fall in the original's month. | Date (Month, Year)<br>EventType (Code = CR)<br>Media (MediaID), through the PostMedia bridge | Post | SUM(Post) by file and month<br>MAX over the files of each month |
| 17 | A13 (SSIS) | Quoting post, quoted post and difference between their numbers of likes, for the quotes where the quoting post received more likes than the quoted post. | The quoted post is stored as an attribute of the quoting post (QuotedPost), which is possible because each post quotes at most one post. Only the 2,179 quotes whose quoted post is in the dataset can be compared, and self-quotes should be left out. It needs SSIS, because an MDX query cannot easily put the likes of two different posts on the same row. A summary version is the share of quotes that beat the quoted post, by quoted account (Trump is quoted 718 times). | Post (TruthID, QuotedPost)<br>Author (UserID) | Like | per post: SUM(Like)<br>likes of the quoting post − likes of the quoted post, kept when > 0 |

## Fact granularity

| | Fact granularity |
|---|---|
| Description | A fact is a single event on a post: its creation, a like, a ReTruth or a reply. |
| Preliminary dimensions | Date, PostDate, EventType, User, Author, Post, Media (through a bridge) |
| Preliminary measures | None. Every metric counts events through the indicators above. |

## What this means for the design

- **PostDate is new.** Questions 12, 13 and 15 place likes on the date of the post they went to,
  and the design so far has only the date of the event. `post_date_id` goes into `Event_X` as a
  second key to `Date_X`, in the same way `author_id` is a second key to `User_X`.
- **The calendar events go into Date_X.** Questions 11, 12 and 13 need `calendar_event` and
  `days_from_event` as attributes of the Date hierarchy, empty for days outside every window. A1
  computes them per post, but they depend only on the day, so in the warehouse they are columns of
  `Date_X`. This works because A1 gives each day to at most one event (the nearest), so a day
  determines its event. Since `Date_X` plays both roles, Date and PostDate both get them.
- **Hour is not needed.** Questions 1 and 13 use the post's day part (`PostDayPart` in `Post_X`),
  and the hour of a like carries no information. The `Hour_X` table can be dropped.
- **Post_X gets three more columns** for the second-round candidates: `n_hashtags` (question 14),
  `n_mentions` (question 15) and `quoted_truth_id` (question 17), a key back to `Post_X` that is
  empty for posts that quote nothing. They cost little, and with them any candidate can be chosen
  after the freeze. `Source` is now used too (question 14).
- **Some attributes are used by no question:** Weekday, FollowingCount, CreatedMonth, IsReply and
  Cluster. They cost little and can stay as descriptions, but nothing requires them.
- **States from A1 are left out.** No question uses them, so they are only described in A1.

## Data facts behind these choices

- **Reaction times are generated.** Likes, ReTruths and replies are dated a median of 59 days after
  their post, and only 1.1% fall on the same day. Questions about posts use the date and time the
  post was created.
- **Likers are random.** The users who like, repost or reply were drawn from a pool of about 2,000
  users, and 15% of these events have an unknown user. No question depends on who acted.
- **Coverage changes over time.** The 2022 crawl covers February to October 2022, the 2024 crawl
  mostly June to August 2024, and Donald Trump's archive runs from 2022 to 2026. Only the 2022 crawl
  has media, quotes and ReTruths from accounts other than Trump, and nearly every 2024-crawl post
  contains a hashtag.
