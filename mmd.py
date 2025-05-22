# Tabs for displaying Match Records, Rankings, and Player Stats
tab1, tab2, tab3 = st.tabs(["📖 Match Records", "🏆 Rankings", "🎾 Player Stats"])

with tab1:
    st.subheader("All Match Records")
    if not matches.empty:
        display = matches.copy()
        display["Date"] = pd.to_datetime(display["date"], errors='coerce')
        display["Date"] = display["Date"].dt.strftime("%d %b %Y")
        display["Match"] = display.apply(
            lambda row: f"{row['team1_player1']} & {row['team1_player2']} vs {row['team2_player1']} & {row['team2_player2']}",
            axis=1
        )
        display["Winner"] = display.apply(
            lambda row: f"🏆 {row['team1_player1']} & {row['team1_player2']}" if row['winner'] == "Team 1" else f"🏆 {row['team2_player1']} & {row['team2_player2']}",
            axis=1
        )
        display = display[["Date", "Match", "set1", "set2", "set3", "Winner", "match_id"]]
        st.dataframe(display, use_container_width=True)

with tab2:
    st.subheader("Player Rankings")
    stats = compute_stats(matches)
    if stats:
        rankings = pd.DataFrame([
            {"Player": p, "Points": d["points"], "Wins": d["wins"], "Losses": d["losses"], "Matches": d["matches"],
             "Win %": f"{(d['wins']/d['matches']*100):.1f}%" if d["matches"] else "0.0%"}
            for p, d in stats.items()
        ])
        rankings = rankings.sort_values(by=["Points", "Wins"], ascending=False)
        rankings.index = range(1, len(rankings) + 1)
        rankings.index.name = "Rank"
        st.dataframe(rankings, use_container_width=True)

with tab3:
    st.subheader("Player Insights")
    selected_player = st.selectbox("Select Player", players, key="player_stats_dropdown")
    if selected_player:
        data = stats.get(selected_player, {"points": 0, "wins": 0, "losses": 0, "matches": 0})
        st.write(f"**Points:** {data['points']}")
        st.write(f"**Wins:** {data['wins']}")
        st.write(f"**Losses:** {data['losses']}")
        st.write(f"**Matches Played:** {data['matches']}")
        win_pct = (data["wins"] / data["matches"] * 100) if data["matches"] else 0
        st.write(f"**Win %:** {win_pct:.1f}%")

        # Analyze partners
        partner_counts = defaultdict(lambda: {"matches": 0, "wins": 0})
        for _, row in matches.iterrows():
            team1 = [row["team1_player1"], row["team1_player2"]]
            team2 = [row["team2_player1"], row["team2_player2"]]
            if selected_player in team1:
                partner = team1[1] if team1[0] == selected_player else team1[0]
                partner_counts[partner]["matches"] += 1
                if row["winner"] == "Team 1":
                    partner_counts[partner]["wins"] += 1
            elif selected_player in team2:
                partner = team2[1] if team2[0] == selected_player else team2[0]
                partner_counts[partner]["matches"] += 1
                if row["winner"] == "Team 2":
                    partner_counts[partner]["wins"] += 1

        if partner_counts:
            st.write("**Partners Played With:**")
            partner_df = pd.DataFrame([
                {
                    "Partner": partner,
                    "Matches": v["matches"],
                    "Wins": v["wins"],
                    "Win %": f"{(v['wins']/v['matches']*100):.1f}%" if v["matches"] else "0.0%"
                }
                for partner, v in partner_counts.items()
            ])
            st.dataframe(partner_df)

            best_partner = max(partner_counts.items(), key=lambda x: (x[1]["wins"]/x[1]["matches"]) if x[1]["matches"] else 0)
            st.write(f"**Most Effective Partner:** {best_partner[0]} ({best_partner[1]['wins']} wins / {best_partner[1]['matches']} matches)")
