import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import plotly.express as px
import plotly.graph_objects as go
import requests

import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")
st.header('Music Analytics App')

# sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=st.secrets['CLIENT_ID'],client_secret=st.secrets['CLIENT_SECRET']))
# access_token = 'BQDLhaCDCpYj-Tt_CIQAg8tFk4KMdRPze5aH-Yr9XHqi2Ca6LcTIXP3Za6PMBriinmXKqOrMxBZMKDcEXGkgU_kJt9rxUXiw8OkuSYouJ3D6DgTCiTVgYQxnkhx6JMCa5YpdiBNW_G_0r7Tgk6i9Zw6T0Yt2tjJg6OTsB0UV3ZFNZxnwoYWWsEO7gZJix7EUZv494YifAku4lbbbFS6bch3nzcfG48mhr_nCHOO4s-Zq1I_8Za3TJp7iD3yvy8M1XQ0DqwaktmI0CAj_Gof6PmwukBrCxH1cVB26IF1QJYe8irieIWbVq9STZblc_eimhG98E1qcve5K50k'
# # url = 'https://open.spotify.com/get_access_token'
access_token = requests.get('https://open.spotify.com/get_access_token').json()['accessToken']

sp = spotipy.Spotify(auth=access_token)

search_choices = ['Song', 'Album', 'Artist/Band']
search_selected = st.sidebar.selectbox("Search by: ", search_choices)
search_keyword = st.text_input("Which " + search_selected.lower() + " do you have in mind?")

params = {
    'Song': {'search_by': "track", 'search_results': "{} - {}", 'item_choices': ['Song Features', 'Song Comparison']},
    'Album': {'search_by': 'album', 'search_results': "{} - {} ({})", 'item_choices': ['Album Features', 'Album Comparison']},
    'Artist/Band': {'search_by': 'artist', 'search_results': "{}", 'item_choices': ['Artist/Band Features', 'Artist/Band Comparison']}
}

def collect_input(search_keyword):
    items = sp.search(q=search_keyword,type=params[search_selected]['search_by'], limit=20)
    items_list = items[f'{params[search_selected]['search_by']}s']['items']
    search_results = []

    for item in items_list:
        if item is not None:
            if search_selected == 'Song':
                search_results.append(params[search_selected]['search_results'].format(item['name'], item['artists'][0]['name']))
            elif search_selected == 'Album':
                search_results.append(params[search_selected]['search_results'].format(item['name'], item['artists'][0]['name'], item['album_type']))
            elif search_selected == 'Artist/Band':
                search_results.append(params[search_selected]['search_results'].format(item['name']))

    selected_item = st.selectbox(f"Select your {search_selected}: ", search_results)

    for item in items_list:
        if item is not None:
            if search_selected == 'Song':
                str_temp = f"{item['name']} - {item['artists'][0]['name']}"
            elif search_selected == 'Album':
                str_temp = f"{item['name']} - {item['artists'][0]['name']} ({item['album_type']})"
            elif search_selected == 'Artist/Band':
                str_temp = item['name']

            if str_temp == selected_item:
                item_data = item

    return item_data

def collect_analysis_info():
    item_data = collect_input(search_keyword)
    selected_analysis = None

    if item_data is not None:
        selected_analysis = st.sidebar.selectbox('Select your action: ', params[search_selected]['item_choices'])  

    return selected_analysis, item_data

def analysis_choice_workflow():
    items = sp.search(q=f'{params[search_selected]['search_by']}:'+ search_keyword,type=params[search_selected]['search_by'], limit=10)
    items_list = items[f'{params[search_selected]['search_by']}s']['items']
    search_results = []

    for item in items_list:
        if item is not None:
            if search_selected in ['Song', 'Album']:
                search_results.append(params[search_selected]['search_results'].format(item['name'], item['artists'][0]['name']))
            elif search_selected == 'Artist/Band':
                search_results.append(params[search_selected]['search_results'].format(item['name']))

    selected_item = st.selectbox(f"Select your {search_selected}: ", search_results)

    for item in items_list:
        if item is not None:
            str_temp = item['name'] + " - " + item['artists'][0]['name'] if search_selected in ['Song', 'Album'] else item['name']
            if str_temp == selected_item:
                item_data = item

    if item_data is not None:
        selected_analysis = st.sidebar.selectbox('Select your action: ', params[search_selected]['item_choices'])    
        return selected_analysis, item_data        
    
def song_features(item_data):
    item_id = item_data['id']

    track_features  = sp.audio_features(item_id) 
    track_data = sp.track(item_id)
    df = pd.DataFrame(track_features, index=[0])
    valid_features = ['acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence']
    df_features = df[valid_features]

    st.subheader(f"{item_data['name']} ({track_data['album']['release_date'][:4]})")
    st.markdown(f"##### By {track_data['artists'][0]['name']} - Album/EP: {track_data['album']['name']}")
    col1, col2, col3 = st.columns([1.5, 1, 1])
    with col1:
        st.image(item_data['album']['images'][1]['url'], use_container_width=True)
    with col2:
        st.metric("Popularity (0-1)", track_data['popularity']/100)
        st.metric("Tempo (bpm)", df.iloc[0]['tempo'])
        st.metric("Key (0-11)", df.iloc[0]['key'])
        st.metric("Explicit", track_data['explicit'])
    with col3:
        st.metric("Album Release", track_data['album']['release_date'])
        st.metric("Loudness", df.iloc[0]['loudness'])
        st.metric("Duration (s)", round(track_data['duration_ms']/1000))
        st.metric("Mode", df.iloc[0]['mode'])

    fig = px.line_polar(df_features, r=df_features.iloc[0].tolist(), theta=valid_features, line_close=True,
                        markers=True,
                        template="plotly_dark")
    fig.update_layout(height=700, font_size=16, legend=dict(orientation="h"))
    fig.update_traces(fill='toself')
    st.plotly_chart(fig)
    st.dataframe(df_features, hide_index=True, use_container_width=True)

def item_comparison():
    comparison_keyword = st.text_input("Which " + search_selected.lower() + " do you want to compare with?")

    if comparison_keyword is not None and len(str(comparison_keyword)) > 0:
        return collect_input(comparison_keyword)
    
def song_comparison(item_data):
    item_comparison_data = item_comparison()
    if item_comparison_data is not None:
        item_id_1 = item_data['id']
        item_id_2 = item_comparison_data['id']

        track_features_1  = sp.audio_features(item_id_1) 
        track_data_1 = sp.track(item_id_1)
        track_features_2  = sp.audio_features(item_id_2) 
        track_data_2 = sp.track(item_id_2)
        df_1 = pd.DataFrame(track_features_1, index=[0])
        df_2 = pd.DataFrame(track_features_2, index=[0])
        df_1['name'] = item_data['name']
        df_2['name'] = item_comparison_data['name']

        combined_df = pd.concat([df_1, df_2], ignore_index=True)

        valid_features = ['acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence']
        
        df_features = combined_df[valid_features]
        df_features = pd.concat([df_features, combined_df['name']], axis=1)

        initcol1, initcol2 = st.columns(2)
        col1, col2 = st.columns(2)
        col11,col12, coldivider, col21,col22 = st.columns([0.95, 0.95, 0.2, 0.95,0.95])

        with initcol1:
            st.subheader(f"{item_data['name']}")
            st.markdown(f"##### By {track_data_1['artists'][0]['name']} - Album/EP: {track_data_1['album']['name']}")
        with initcol2:
            st.subheader(f"{item_comparison_data['name']}")
            st.markdown(f"##### By {track_data_2['artists'][0]['name']} - Album/EP: {track_data_2['album']['name']}")
        with col1:
            st.image(item_data['album']['images'][1]['url'], caption=f"Track ID: {item_id_1}", use_container_width=True)
            with col11:
                st.metric("Album Release", track_data_1['album']['release_date'])
                st.metric("Popularity (0-1)", track_data_1['popularity']/100)
                st.metric("Loudness", df_1.iloc[0]['loudness'])
                st.metric("Tempo (bpm)", df_1.iloc[0]['tempo'])
            with col12:
                st.metric("Key (0-11)", df_1.iloc[0]['key'])
                st.metric("Duration (s)", round(track_data_1['duration_ms']/1000))
                st.metric("Mode", df_1.iloc[0]['mode'])
                st.metric("Explicit", track_data_1['explicit'])
            with coldivider:
                st.html(
            '''
                <div class="divider-vertical-line"></div>
                <style>
                    .divider-vertical-line {
                        border-left: 2px solid rgba(255, 255, 255, 0.2);
                        height: 350px;
                        margin: auto;
                    }
                </style>
            '''
        )
        with col2:
            st.image(item_comparison_data['album']['images'][1]['url'], caption=f"Track ID: {item_id_2}", use_container_width=True)
            with col21:
                st.metric("Album Release", track_data_2['album']['release_date'])
                st.metric("Popularity (0-1)", track_data_2['popularity']/100)
                st.metric("Loudness", df_2.iloc[0]['loudness'])
                st.metric("Tempo (bpm)", df_2.iloc[0]['tempo'])
            with col22:
                st.metric("Key (0-11)", df_2.iloc[0]['key'])
                st.metric("Duration (s)", round(track_data_2['duration_ms']/1000))
                st.metric("Mode", df_2.iloc[0]['mode'])
                st.metric("Explicit", track_data_2['explicit'])

        df_long = df_features.melt(id_vars='name', var_name='feature', value_name='value')
        fig = px.line_polar(df_long, r='value', theta='feature', color='name', line_close=True, template="plotly_dark")
        fig.update_layout(height=700, font_size=16, legend=dict(orientation="h"))

        st.plotly_chart(fig)
        st.dataframe(df_features, hide_index=True, use_container_width=True)

def album_features(item_data):
    album_id = item_data['id']
    album_tracks = sp.album_tracks(album_id)

    #Initial info part 1
    st.subheader(f"{item_data['name']} - {item_data['artists'][0]['name']}")
    col1, col2 = st.columns(2)
    with col1:
        st.image(item_data['images'][1]['url'], use_container_width=True)

    track_data = []
    for track in album_tracks['items']:
        track_additional_data = sp.track(track['id'])

        track_data.append({
            'track_id': track['id'],
            'track_name': track['name'],
            'track_number': track['track_number'],
            'popularity': track_additional_data['popularity']
        })

    df_tracks = pd.DataFrame(track_data)

    track_ids = df_tracks['track_id'].tolist()
    audio_features = sp.audio_features(track_ids)
    valid_features = ['acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence']

    for feature in valid_features:
        df_tracks[feature] = [track[feature] if track else None for track in audio_features]
    
    df_tracks['tempo'] = [track['tempo'] for track in audio_features]
    valid_features.append('popularity')
    df_tracks['popularity'] = [track['popularity']/100 for track in track_data]

    df_tracks['track_label'] = df_tracks['track_number'].astype(str) + ". " + df_tracks['track_name']
    df_tracks = df_tracks.set_index('track_number')
    df_features = df_tracks[valid_features].round(3).T

    #Initial info part 2
    with col2:
        st.metric("Tracks", item_data['total_tracks'])
        st.metric("Release Date (yyyy/mm/dd)", item_data['release_date'])
        st.metric("Available Markets", len(item_data['available_markets']))
        st.metric("Average Track Popularity", df_tracks['popularity'].mean().round(3))
        st.metric("Average BPM", df_tracks['tempo'].mean().round(3))
        st.metric("Album Type", item_data['album_type'])

    #Heatmap
    fig_heatmap = px.imshow(df_features,
                    color_continuous_scale='RdBu_r',
                    text_auto=True,
                    )    
    

    fig_heatmap.update_layout(xaxis_title ='Song/Track',
                      xaxis = dict(tickmode='linear'),                    
                      title = 'Album Features Heatmap'
                      )

    st.plotly_chart(fig_heatmap, use_container_width=True)

    #Polar Chart with Average Values
    average_values = df_tracks[valid_features].mean()
    fig_polar = go.Figure()
    fig_polar.add_trace(go.Scatterpolar(
        r=average_values,
        theta=valid_features,
        fill='toself',
        name='Average Audio Features',
        line_color='blue',
    ))

    fig_polar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True),
        ),
        title="Average Album Audio Features",
        template = 'plotly_dark',
        height = 700,
        font_size = 16
    )

    st.plotly_chart(fig_polar)

    #Dataframe with values printed
    print_features = ['track_label','acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence', 'tempo', 'popularity']
    df_print = df_tracks[print_features]
    st.dataframe(df_print, hide_index=True, use_container_width=True)

def album_comparison(item_data):
    item_comparison_data = item_comparison()
    if item_comparison_data is not None:
        item_id_1 = item_data['id']
        item_id_2 = item_comparison_data['id']

        album_1_title = f"{item_data['name']} - {item_data['artists'][0]['name']}"
        album_2_title = f"{item_comparison_data['name']} - {item_comparison_data['artists'][0]['name']}"

        album_tracks_1 = sp.album_tracks(item_id_1)
        album_tracks_2 = sp.album_tracks(item_id_2)

        track_data_1 = []
        for track in album_tracks_1['items']:
            track_additional_data = sp.track(track['id'])

            track_data_1.append({
                'track_id': track['id'],
                'track_name': track['name'],
                'track_number': track['track_number'],
                'popularity': track_additional_data['popularity'],
                'album_id': item_id_1,
                'album_name': item_data['name'],
            })

        track_data_2 = []
        for track in album_tracks_2['items']:
            track_additional_data = sp.track(track['id'])

            track_data_2.append({
                'track_id': track['id'],
                'track_name': track['name'],
                'track_number': track['track_number'],
                'popularity': track_additional_data['popularity'],
                'album_id': item_id_2,
                'album_name': item_comparison_data['name'],
            })

        df_tracks_1 = pd.DataFrame(track_data_1)
        df_tracks_2 = pd.DataFrame(track_data_2)

        track_ids_1 = df_tracks_1['track_id'].tolist()
        track_ids_2 = df_tracks_2['track_id'].tolist()

        audio_features_1 = sp.audio_features(track_ids_1)
        audio_features_2 = sp.audio_features(track_ids_2)

        valid_features = ['acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence']

        for feature in valid_features:
            df_tracks_1[feature] = [track[feature] if track else None for track in audio_features_1]
            df_tracks_2[feature] = [track[feature] if track else None for track in audio_features_2]
        
        valid_features.append('popularity')
        df_tracks_1['popularity'] = [track['popularity']/100 for track in track_data_1]
        df_tracks_2['popularity'] = [track['popularity']/100 for track in track_data_2]
        df_tracks_1['tempo'] = [track['tempo'] for track in audio_features_1]
        df_tracks_2['tempo'] = [track['tempo'] for track in audio_features_2]
        df_tracks_1['track_label'] = df_tracks_1['track_number'].astype(str) + ". " + df_tracks_1['track_name']
        df_tracks_2['track_label'] = df_tracks_2['track_number'].astype(str) + ". " + df_tracks_2['track_name']
        
        hover_text_1 = []
        hover_text_2 = []
        for feature in valid_features:
            hover_text_1.append([
                f"Feature: {feature}<br>Track: {df_tracks_1.loc[idx, 'track_label']}<br>Album: {album_1_title}<br>Value: {df_tracks_1.loc[idx, feature]:.3f}" 
                for idx in df_tracks_1.index
            ])
            hover_text_2.append([
                f"Feature: {feature}<br>Track: {df_tracks_2.loc[idx, 'track_label']}<br>Album: {album_2_title}<br>Value: {df_tracks_2.loc[idx, feature]:.3f}" 
                for idx in df_tracks_2.index
            ])
        
        # Build the heatmap
        fig_1 = go.Figure(data=go.Heatmap(
            z=df_tracks_1[valid_features].T.values,
            x=df_tracks_1["track_number"],
            y=valid_features,
            # texttemplate="%{z:.2f}",
            colorscale="RdBu_r", 
            text=hover_text_1,  
            showscale=False,
            hoverinfo="text"  
        ))

        # Update layout
        fig_1.update_layout(
            title="Feature Heatmap per Track",
            # xaxis_title="Track Number",
            # yaxis_title="Features",
            # xaxis=dict(tickmode="array", tickvals=df_tracks["track_number"], ticktext=df_tracks["track_number"]),
            # yaxis=dict(tickmode="array", tickvals=valid_features, ticktext=valid_features),
            # autosize=True,
            xaxis_visible=False,
            margin=dict(l=50, r=0, t=50, b=50)
        )

        # Build the heatmap 2
        fig_2 = go.Figure(data=go.Heatmap(
            z=df_tracks_2[valid_features].T.values,
            x=df_tracks_2["track_number"],
            y=valid_features,
            # texttemplate="%{z:.2f}",
            colorscale="RdBu_r",  # Choose a color scale
            text=hover_text_2,  # Custom hover info
            hoverinfo="text"  # Display custom hover info
        ))

        # Update layout
        fig_2.update_layout(
            # title="Audio Features Heatmap 2",
            # xaxis_title="Track Number",
            # yaxis_title="Features",
            # xaxis=dict(tickmode="array", tickvals=df_tracks["track_number"], ticktext=df_tracks["track_number"]),
            # yaxis=dict(tickmode="array", tickvals=valid_features, ticktext=valid_features),
            # autosize=True,
            yaxis_visible=False,
            xaxis_visible=False,
            margin=dict(l=25, r=50, t=50, b=50)
        )

        initcol1, initcol2 = st.columns(2)
        col1, col2 = st.columns(2)
        col11, col12, col21, col22 = st.columns(4)
        col3, col4 = st.columns(2)

        with initcol1:
            st.markdown(f"### {album_1_title}")
        with initcol2:
            st.markdown(f"### {album_2_title}")
        with col1:
            st.image(item_data['images'][1]['url'], caption=f"ID: {item_id_1}", use_container_width=True)
        with col11:
            st.metric("Tracks", item_data['total_tracks'])
            st.metric("Average Track Popularity", df_tracks_1['popularity'].mean().round(3))
            st.metric("Average BPM", df_tracks_1['tempo'].mean().round(3))
        with col12:
            st.metric("Available Markets", len(item_data['available_markets']))
            st.metric("Release Date (yyyy/mm/dd)", item_data['release_date'])
        with col2:
            st.image(item_comparison_data['images'][1]['url'], caption=f"ID: {item_id_2}", use_container_width=True)
        with col21:
            st.metric("Tracks", item_comparison_data['total_tracks'])
            st.metric("Average Track Popularity", df_tracks_2['popularity'].mean().round(3))
            st.metric("Average BPM", df_tracks_2['tempo'].mean().round(3))
        with col22:
            st.metric("Available Markets", len(item_comparison_data['available_markets']))
            st.metric("Release Date (yyyy/mm/dd)", item_comparison_data['release_date'])
        with col3:
            st.plotly_chart(fig_1)
        with col4:
            st.plotly_chart(fig_2)
        
        combined_df = pd.concat([df_tracks_1, df_tracks_2], ignore_index=True)
        grouped_df = combined_df.groupby("album_id").agg(
                                                        album_name=("album_name", "first"),
                                                        popularity=("popularity", "mean"),
                                                        acousticness=("acousticness", "mean"), 
                                                        danceability=("danceability", "mean"), 
                                                        energy=("energy", "mean"),
                                                        instrumentalness=("instrumentalness", "mean"), 
                                                        liveness=("liveness", "mean"),
                                                        speechiness=("speechiness", "mean"), 
                                                        valence=("valence", "mean") 
                                                        ).reset_index()
        df_long = grouped_df.melt(id_vars=['album_id', 'album_name'], var_name='feature', value_name='value')
        fig_polar = px.line_polar(df_long, r='value', theta='feature', color='album_name', line_close=True, template="plotly_dark")
        fig_polar.update_layout(title = 'Polar Chart - Average Features',legend=dict(orientation="h"), height = 700, font_size = 16, autosize=True) 
        st.plotly_chart(fig_polar, use_container_width=True)

@st.cache_data
def artist_features(item_data):
    item_id = item_data['id']
    st.subheader(f"{item_data['name']}")
    st.markdown(f"###### {', '.join(item_data['genres'])}")

    full_albums = 0
    single_collections = 0
    valid_features = ['acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence', 'tempo', 'loudness', 'duration_ms']

    artist_albums = sp.artist_albums(item_id)
    artist_df = pd.DataFrame()

    for album in artist_albums['items']:
        if album['album_type'] == 'album':
            full_albums += 1
        elif album['album_type'] == 'single':
            single_collections += 1
            continue

        tracks = sp.album_tracks(album['id'])

        track_data = []
        for track in tracks['items']:
            track_data.append({
                "Album ID": album['id'],
                "Album": album['name'],
                "Release Date": album['release_date'],
                "Track ID": track['id'],
                "Track": track['name']
            })

        album_df = pd.DataFrame(track_data)
        # artist_df = pd.concat([artist_df, album_df], ignore_index=True)
        track_ids = album_df["Track ID"].tolist()

        album_features = sp.audio_features(track_ids)
        features_df = pd.DataFrame(album_features).set_index("id")[valid_features]
        album_df = album_df.set_index("Track ID").join(features_df, how="left").reset_index()

        # for track in album_features:
        #     for feature in valid_features:
        #         album_df.loc[album_df['Track ID'] == track['id'], feature] = track[feature]
        #         # artist_df.loc[artist_df['Track ID'] == track['id'], feature] = track[feature]

        album_tracks_details = sp.tracks(track_ids)
        popularity_df = pd.DataFrame(album_tracks_details['tracks'])[['id', 'popularity']].set_index("id")
        popularity_df["popularity"] = popularity_df["popularity"] / 100
        album_df = album_df.set_index("Track ID").join(popularity_df, how="left").reset_index()


        # for track_detail in album_tracks_details['tracks']:
        #     album_df.loc[album_df['Track ID'] == track_detail['id'], 'popularity'] = track_detail['popularity']/100
        #     # artist_df.loc[artist_df['Track ID'] == track_detail['id'], 'popularity'] = track_detail['popularity']/100

        artist_df = pd.concat([artist_df, album_df], ignore_index=True)

    
    if artist_df.empty:
        st.warning("No albums found for this artist.")
        return

    col1, col2 = st.columns(2)

    with col1:
        try:
            st.image(item_data['images'][0]['url'], use_container_width=True)
        except:
            print('error adding img')
            print(item_data)

    with col2:
        st.metric("Popularity", item_data['popularity']/100)
        st.metric("Spotify Followers", f"{item_data['followers']['total']:,}")
        st.metric("Albums", full_albums)
        st.metric("Single Collections", single_collections)

    if len(artist_df) > 0:
        artist_df['Release Date'] = pd.to_datetime(artist_df['Release Date'], errors='coerce')

        # Handle NaT by parsing as year
        artist_df['Release Date'] = artist_df['Release Date'].fillna(
            pd.to_datetime(artist_df['Release Date'][:4], format='%Y', errors='coerce')
        )
        artist_df = artist_df.sort_values('Release Date')
        st.write("Select a band/artist and an audio feature to visualize their albums.")

    valid_features.append('popularity')
    return artist_df, valid_features

def get_input_feature_and_plot(artist_df, valid_features):
    if len(artist_df) > 0:
        artist_df['Release Year'] = artist_df['Release Date'].dt.year
        artist_df['Album (Year)'] = artist_df.apply(
            lambda row: f"{row['Album'][:12]}.. ({row['Release Year']})" if len(row['Album']) > 15 
                        else f"{row['Album']} ({row['Release Year']})", 
            axis=1
        )

        feature = st.selectbox("Select an attribute to plot:", valid_features)
        fig_boxplot = px.box(artist_df, 
                        x="Album (Year)", 
                        y=feature, 
                        color="Album (Year)",
                        custom_data=["Album"]
                        )
        # fig.update_traces(hovertemplate=(
        #                         "<b>Album:</b> %{customdata[0]}<br>" 
        #                         "<b>Median:</b> %{y}<br>" 
        #                         "<b>Average:</b> %{yavg}<extra></extra>"  
        #                     )
        #                 )
        
        st.plotly_chart(fig_boxplot)

        fig_violin = px.violin(artist_df, 
                    x="Album (Year)", 
                    y=feature, 
                    color="Album (Year)", 
                    box=True,  # Include a boxplot inside the violin
                    points="all",  # Show individual data points
                    custom_data=["Album"]

                )
        
        fig_violin.update_layout(
            xaxis_title="Album (Year)",
            yaxis_title=feature.capitalize(),
            xaxis_tickangle=-45
        )

        fig_violin.update_traces(hovertemplate=(
                        "<b>Album:</b> %{customdata[0]}<br>" 
                        "<b>Median:</b> %{y}<br>" 
                        "<b>Average:</b> %{yavg}<extra></extra>"  
                    )
                )

        st.plotly_chart(fig_violin)

        #scatter + line

        album_avg = artist_df.groupby("Album (Year)")[feature].mean().reset_index()
        album_avg = album_avg.merge(artist_df[['Album (Year)', 'Release Date']].drop_duplicates(), on="Album (Year)")

        scatter_df = artist_df.sort_values(by='Release Date')

        album_avg = album_avg.sort_values(by='Release Date')

        fig_scatter = px.scatter(
            scatter_df, 
            x="Album (Year)", 
            y=feature, 
            color="Album (Year)",  
            title=f"Track {feature.capitalize()} Values per Album",
            hover_data=["Album", "Track"],  
        )

        fig_scatter.add_trace(go.Scatter(
            x=album_avg["Album (Year)"],  
            y=album_avg[feature],  
            mode="lines",  
            name=f"Average {feature.capitalize()} per Album",  
            line=dict(color="white", width=2),  
        ))

        fig_scatter.update_layout(
            xaxis_title=None,
            yaxis_title=feature.capitalize(),
            # xaxis_tickangle=-45,  # Rotate x-axis labels
            showlegend=False,  # Show legend
            # height=600,  # Adjust height if necessary
        )

        st.plotly_chart(fig_scatter, use_container_width=True)

        #Heatmap
        heatmap_df = artist_df.set_index('Album (Year)')
        heatmap_df = heatmap_df[['acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence', 'popularity']].round(3).T
        
        fig_heatmap = px.imshow(heatmap_df,
                        color_continuous_scale='RdBu_r',
                        text_auto=True,
                        )    

        fig_heatmap.update_layout(
            autosize=True, 
            xaxis=dict(scaleanchor=None),  
            yaxis=dict(scaleanchor=None),
            title = 'Feature Heatmap Across Albums'

        )

        st.plotly_chart(fig_heatmap, use_container_width=True)

        st.dataframe(artist_df[['Album', 'Release Year', 'Track', 'acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence', 'loudness', 'duration_ms']])


def artist_comparison(item_data):
    pass


if __name__ == "__main__":
    selected_analysis = None
    item_data = None

    if search_keyword is not None and len(str(search_keyword)) > 0:
        selected_analysis, item_data = collect_analysis_info()

    if selected_analysis == 'Song Features':
        song_features(item_data)
    elif selected_analysis == 'Song Comparison':
        song_comparison(item_data)
    elif selected_analysis == 'Album Features':
        album_features(item_data)
    elif selected_analysis == 'Album Comparison':
        album_comparison(item_data)
    elif selected_analysis == 'Artist/Band Features':
        artist_df, valid_features = artist_features(item_data)
        get_input_feature_and_plot(artist_df, valid_features)
    elif selected_analysis == 'Artist/Band Comparison':
        artist_comparison(item_data)