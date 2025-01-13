import spotipy
import plotly.express as px
import plotly.graph_objects as go
import requests
import lyricsgenius

from sklearn.preprocessing import StandardScaler
from sklearn.manifold import TSNE

import pandas as pd
import streamlit as st

from help_text import FEATURES_DESCRIPTION

st.set_page_config(layout="wide")
st.header('Music Analytics App')

access_token = requests.get('https://open.spotify.com/get_access_token').json()['accessToken']
sp = spotipy.Spotify(auth=access_token)

genius_access_token = st.secrets['GENIUS_TOKEN']
genius = lyricsgenius.Genius(genius_access_token, remove_section_headers=True, skip_non_songs=True)

search_choices = ['Song', 'Album', 'Artist/Band']
search_selected = st.sidebar.selectbox("Search by: ", search_choices)
search_keyword = st.text_input("Which " + search_selected.lower() + " do you have in mind?")

params = {
    'Song': {'search_by': "track", 'search_results': "{} - {} (ID {})", 'item_choices': ['Song Features', 'Song Comparison']},
    'Album': {'search_by': 'album', 'search_results': "{} - {} ({})", 'item_choices': ['Album Features', 'Album Comparison']},
    'Artist/Band': {'search_by': 'artist', 'search_results': "{} (ID {})", 'item_choices': ['Artist/Band Features', 'Artist/Band Comparison']}
}

def collect_input(search_keyword):
    items = sp.search(q=search_keyword,type=params[search_selected]['search_by'], limit=20)
    items_list = items[f'{params[search_selected]['search_by']}s']['items']
    search_results = []

    for item in items_list:
        if item is not None:
            if search_selected == 'Song':
                search_results.append(params[search_selected]['search_results'].format(item['name'], item['artists'][0]['name'], item['id']))
            elif search_selected == 'Album':
                search_results.append(params[search_selected]['search_results'].format(item['name'], item['artists'][0]['name'], item['album_type']))
            elif search_selected == 'Artist/Band':
                search_results.append(params[search_selected]['search_results'].format(item['name'], item['id']))

    selected_item = st.selectbox(f"Select your {search_selected}: ", search_results)

    for item in items_list:
        if item is not None:
            if search_selected == 'Song':
                str_temp = f"{item['name']} - {item['artists'][0]['name']} (ID {item['id']})"
            elif search_selected == 'Album':
                str_temp = f"{item['name']} - {item['artists'][0]['name']} ({item['album_type']})"
            elif search_selected == 'Artist/Band':
                str_temp = f"{item['name']} (ID {item['id']})"

            if str_temp == selected_item:
                item_data = item

    return item_data

def collect_analysis_info():
    item_data = collect_input(search_keyword)
    selected_analysis = None

    if item_data is not None:
        selected_analysis = st.sidebar.selectbox('Select your action: ', params[search_selected]['item_choices'])  
        with st.sidebar:
            st.caption(FEATURES_DESCRIPTION, unsafe_allow_html=True)

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

    song_lyrics = genius.search_song(item_data['name'], track_data['artists'][0]['name'])
    if song_lyrics:
        st.markdown("##### Lyrics")
        st.markdown(f":gray[{song_lyrics.lyrics.replace("\n", "<br>")}]", unsafe_allow_html=True)

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

        col3, col4 = st.columns(2)
        song_lyrics_1 = genius.search_song(item_data['name'], track_data_1['artists'][0]['name'])
        song_lyrics_2 = genius.search_song(item_comparison_data['name'], track_data_2['artists'][0]['name'])

        with col3:
            st.markdown(f"##### {item_data['name']}")
            if song_lyrics_1 is not None:
                st.markdown(f":gray[{song_lyrics_1.lyrics.replace("\n", "<br>")}]", unsafe_allow_html=True)
            else:
                st.markdown(":gray[No lyrics found on database.]")

        with col4:
            st.markdown(f"##### {item_comparison_data['name']}")
            if song_lyrics_2 is not None:
                st.markdown(f":gray[{song_lyrics_2.lyrics.replace("\n", "<br>")}]", unsafe_allow_html=True)
            else:
                st.markdown(":gray[No lyrics found on database.]")

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

    #tsne
    # features_tsne = [ 'acousticness', 'danceability', 'energy','instrumentalness', 'liveness', 'speechiness', 'valence', 'tempo']
    # feature_data = df_tracks[features_tsne]

    # scaler_album_features = StandardScaler()
    # scaled_data = scaler_album_features.fit_transform(feature_data)
    # tsne = TSNE(n_components=2, perplexity=max(len(feature_data)//3, 1), random_state=42)
    # tsne_embedding = tsne.fit_transform(scaled_data)
    # tsne_df = pd.DataFrame(tsne_embedding, columns=['x', 'y'])
    # tsne_df['track_label'] = df_tracks['track_label']

    # fig_tsne = px.scatter(
    #     tsne_df, 
    #     x='x', 
    #     y='y', 
    #     hover_data=['track_label'], 
    #     color = 'track_label',
    # )

    # fig_tsne.update_layout(
    #     title="t-SNE Visualization of Songs",
    #     xaxis_visible=False,
    #     yaxis_visible=False,

    # )

    # st.plotly_chart(fig_tsne)

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
        
        # heatmap 1
        fig_1 = go.Figure(data=go.Heatmap(
            z=df_tracks_1[valid_features].T.values,
            x=df_tracks_1["track_number"],
            y=valid_features,
            colorscale="RdBu_r", 
            text=hover_text_1,  
            showscale=False,
            hoverinfo="text"  
        ))

        fig_1.update_layout(
            title="Feature Heatmap per Track",
            xaxis_visible=False,
            margin=dict(l=50, r=0, t=50, b=50)
        )

        # heatmap 2
        fig_2 = go.Figure(data=go.Heatmap(
            z=df_tracks_2[valid_features].T.values,
            x=df_tracks_2["track_number"],
            y=valid_features,
            colorscale="RdBu_r", 
            text=hover_text_2,  
            hoverinfo="text"  
        ))

        fig_2.update_layout(
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
        
        #polar chart
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
        df_long = df_long.sort_values('album_name')
        fig_polar = px.line_polar(df_long, r='value', theta='feature', color='album_name', line_close=True, template="plotly_dark")
        fig_polar.update_layout(title = 'Polar Chart - Average Features',legend=dict(orientation="h"), height = 700, font_size = 16, autosize=True) 
        st.plotly_chart(fig_polar, use_container_width=True)

        #tsne
        features_dimensionality = [ 'acousticness', 'danceability', 'energy','instrumentalness', 'liveness', 'speechiness', 'valence', 'tempo']
        feature_data = combined_df[features_dimensionality]

        scaler_album_features = StandardScaler()
        scaled_data = scaler_album_features.fit_transform(feature_data)

        tsne = TSNE(n_components=2, perplexity=max(1, len(feature_data)//3), random_state=42)
        tsne_embedding = tsne.fit_transform(scaled_data)
        tsne_df = pd.DataFrame(tsne_embedding, columns=['x', 'y'])
        tsne_df['track_label'] = combined_df['track_label']
        tsne_df['album_name'] = combined_df['album_name']
        tsne_df = tsne_df.sort_values('album_name')

        fig_tsne = px.scatter(
            tsne_df, 
            x='x', 
            y='y', 
            hover_data=['track_label'], 
            color = 'album_name',
            template="plotly_dark"
        )

        fig_tsne.update_layout(
            title="t-SNE Visualization of Album Songs",
            xaxis=dict(
                showgrid=True,
                showticklabels=False,
            ),
            yaxis=dict(
                showgrid=True,
                showticklabels=False,
            ),
        )

        st.plotly_chart(fig_tsne)

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
        track_ids = album_df["Track ID"].tolist()

        album_features = sp.audio_features(track_ids)
        features_df = pd.DataFrame(album_features).set_index("id")[valid_features]
        album_df = album_df.set_index("Track ID").join(features_df, how="left").reset_index()

        album_tracks_details = sp.tracks(track_ids)
        popularity_df = pd.DataFrame(album_tracks_details['tracks'])[['id', 'popularity']].set_index("id")
        popularity_df["popularity"] = popularity_df["popularity"] / 100
        album_df = album_df.set_index("Track ID").join(popularity_df, how="left").reset_index()

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

        artist_df['Release Date'] = artist_df['Release Date'].fillna(
            pd.to_datetime(artist_df['Release Date'][:4], format='%Y', errors='coerce')
        )
        artist_df = artist_df.sort_values('Release Date')
        st.write("Select a band/artist and an audio feature to visualize their albums.")

    valid_features.append('popularity')

    # #backup saving to csv
    # output_file = f"artist_feature_{item_data['name']}.csv"
    # artist_df.to_csv(output_file, index=False)

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

        album_avg = artist_df.groupby("Album (Year)")[feature].mean().reset_index()
        album_avg = album_avg.merge(artist_df[['Album (Year)', 'Release Date']].drop_duplicates(), on="Album (Year)")
        scatter_df = artist_df.sort_values(by='Release Date')
        album_avg = album_avg.sort_values(by='Release Date')

        # fig_boxplot = px.box(artist_df, 
        #                 x="Album (Year)", 
        #                 y=feature, 
        #                 color="Album (Year)",
        #                 custom_data=["Album"]
        #                 )
        
        # st.plotly_chart(fig_boxplot)

        #scatter + line


        # fig_scatter = px.scatter(
        #     scatter_df, 
        #     x="Album (Year)", 
        #     y=feature, 
        #     color="Album (Year)",  
        #     title=f"Track {feature.capitalize()} Values per Album",
        #     hover_data=["Album", "Track"],  
        # )

        # fig_scatter.add_trace(go.Scatter(
        #     x=album_avg["Album (Year)"],  
        #     y=album_avg[feature],  
        #     mode="lines",  
        #     name=f"Average {feature.capitalize()} per Album",  
        #     line=dict(color="gray", width=2),  
        # ))

        # fig_scatter.update_layout(
        #     xaxis_title=None,
        #     yaxis_title=feature.capitalize(),
        #     showlegend=False,  
        #     # height=600,  
        # )

        # st.plotly_chart(fig_scatter, use_container_width=True)

        #violin
        fig_violin = px.violin(artist_df, 
                    x="Album (Year)", 
                    y=feature, 
                    color="Album (Year)", 
                    box=True, 
                    points="all", 
                    custom_data=["Album", "Track"]

                )
        
        fig_violin.update_layout(
            title = "Violin Plot with Average Trend Line",
            xaxis_title="Album (Year)",
            yaxis_title=feature.capitalize(),
            xaxis_tickangle=-45,
            showlegend=False,  

        )

        fig_violin.update_traces(hovertemplate=(
                        "<b>Album:</b> %{customdata[0]}<br>" 
                        "<b>Track:</b> %{customdata[1]}<br>"  
                        "<b>Value:</b> %{y}<br>" 
                    )
                )

        fig_violin.add_trace(go.Scatter(
            x=album_avg["Album (Year)"],  
            y=album_avg[feature],  
            mode="lines",  
            name=f"Average {feature.capitalize()} per Album",  
            line=dict(color="gray", width=2),  
        ))


        st.plotly_chart(fig_violin)

        #Heatmap
        heatmap_df = artist_df.groupby('Album (Year)')[['acousticness', 'danceability', 'energy', 'instrumentalness','liveness', 'speechiness', 'valence', 'popularity']].mean()
        heatmap_df = heatmap_df.merge(artist_df[['Album (Year)', 'Release Date']].drop_duplicates(), on="Album (Year)")
        heatmap_df = heatmap_df.sort_values(by='Release Date')
        heatmap_df = heatmap_df.set_index('Album (Year)')
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

        #tsne
        features_dimensionality = [ 'acousticness', 'danceability', 'energy','instrumentalness', 'liveness', 'speechiness', 'valence', 'tempo']
        feature_data = scatter_df[features_dimensionality]

        scaler_album_features = StandardScaler()
        scaled_data = scaler_album_features.fit_transform(feature_data)

        tsne = TSNE(n_components=2, perplexity=max(1, min(30, len(feature_data)//8)), random_state=42)
        tsne_embedding = tsne.fit_transform(scaled_data)
        tsne_df = pd.DataFrame(tsne_embedding, columns=['x', 'y'])
        tsne_df['Album'] = scatter_df['Album']
        tsne_df['Track'] = scatter_df['Track']

        fig_tsne = px.scatter(
            tsne_df, 
            x='x', 
            y='y', 
            hover_data=['Album', 'Track'], 
            color = 'Album',
            template="plotly_dark"
        )

        fig_tsne.update_layout(
            title="t-SNE Visualization of Artist Discography",
            xaxis=dict(
                showgrid=True,
                showticklabels=False,
            ),
            yaxis=dict(
                showgrid=True,
                showticklabels=False,
            ),
        )

        st.plotly_chart(fig_tsne)

        st.dataframe(artist_df[['Album', 'Release Year', 'Track', 'acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence', 'loudness', 'duration_ms']])

@st.cache_data
def artist_comparison(item_data, item_comparison_data):
    if item_comparison_data is not None:
        item_id_1 = item_data['id']
        item_id_2 = item_comparison_data['id']

        initcol1, initcol2 = st.columns(2)
        col1, col2 = st.columns(2)
        col11, col12, col21, col22 = st.columns(4)

        with initcol1:
            st.subheader(f"{item_data['name']}")
            st.markdown(f"###### {', '.join(item_data['genres'])}")
        with initcol2:
            st.subheader(f"{item_comparison_data['name']}")
            st.markdown(f"###### {', '.join(item_comparison_data['genres'])}")
        with col1:
            st.image(item_data['images'][1]['url'], caption=f"ID: {item_id_1}", use_container_width=True)
        with col2:
            st.image(item_comparison_data['images'][1]['url'], caption=f"ID: {item_id_1}", use_container_width=True)

        full_albums_1 = 0
        full_albums_2 = 0
        single_collections_1 = 0
        single_collections_2 = 0
        valid_features = ['acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence', 'tempo', 'loudness', 'duration_ms']

        artist_albums_1 = sp.artist_albums(item_id_1)
        artist_albums_2 = sp.artist_albums(item_id_2)
        artist_df = pd.DataFrame()

        for album in artist_albums_1['items']:
            if album['album_type'] == 'album':
                full_albums_1 += 1
            elif album['album_type'] == 'single':
                single_collections_1 += 1
                continue

            tracks = sp.album_tracks(album['id'])

            track_data = []
            for track in tracks['items']:
                track_data.append({
                    "Artist ID": item_data['id'],
                    "Artist": item_data['name'],
                    "Artist Number": 1,
                    "Album ID": album['id'],
                    "Album": album['name'],
                    "Release Date": album['release_date'],
                    "Track ID": track['id'],
                    "Track": track['name']
                })

            album_df = pd.DataFrame(track_data)
            track_ids = album_df["Track ID"].tolist()

            album_features = sp.audio_features(track_ids)
            features_df = pd.DataFrame(album_features).set_index("id")[valid_features]
            album_df = album_df.set_index("Track ID").join(features_df, how="left").reset_index()

            album_tracks_details = sp.tracks(track_ids)
            popularity_df = pd.DataFrame(album_tracks_details['tracks'])[['id', 'popularity']].set_index("id")
            popularity_df["popularity"] = popularity_df["popularity"] / 100
            album_df = album_df.set_index("Track ID").join(popularity_df, how="left").reset_index()

            artist_df = pd.concat([artist_df, album_df], ignore_index=True)

        for album in artist_albums_2['items']:
            if album['album_type'] == 'album':
                full_albums_2 += 1
            elif album['album_type'] == 'single':
                single_collections_2 += 1
                continue

            tracks = sp.album_tracks(album['id'])

            track_data = []
            for track in tracks['items']:
                track_data.append({
                    "Artist ID": item_comparison_data['id'],
                    "Artist": item_comparison_data['name'],
                    "Artist Number": 2,
                    "Album ID": album['id'],
                    "Album": album['name'],
                    "Release Date": album['release_date'],
                    "Track ID": track['id'],
                    "Track": track['name']
                })

            album_df = pd.DataFrame(track_data)
            track_ids = album_df["Track ID"].tolist()

            album_features = sp.audio_features(track_ids)
            features_df = pd.DataFrame(album_features).set_index("id")[valid_features]
            album_df = album_df.set_index("Track ID").join(features_df, how="left").reset_index()

            album_tracks_details = sp.tracks(track_ids)
            popularity_df = pd.DataFrame(album_tracks_details['tracks'])[['id', 'popularity']].set_index("id")
            popularity_df["popularity"] = popularity_df["popularity"] / 100
            album_df = album_df.set_index("Track ID").join(popularity_df, how="left").reset_index()

            artist_df = pd.concat([artist_df, album_df], ignore_index=True)
        
        if artist_df.empty:
            st.warning("No albums found for this artist.")
            return

        with col11:
            st.metric("Popularity", item_data['popularity']/100)
            st.metric("Spotify Followers", f"{item_data['followers']['total']:,}")
        with col12:
            st.metric("Albums", full_albums_1)
            st.metric("Single Collections", single_collections_1)
        with col21:
            st.metric("Popularity", item_comparison_data['popularity']/100)
            st.metric("Spotify Followers", f"{item_comparison_data['followers']['total']:,}")
        with col22:
            st.metric("Albums", full_albums_2)
            st.metric("Single Collections", single_collections_2)

        if len(artist_df) > 0:
            artist_df['Release Date'] = pd.to_datetime(artist_df['Release Date'], errors='coerce')

            artist_df['Release Date'] = artist_df['Release Date'].fillna(
                pd.to_datetime(artist_df['Release Date'][:4], format='%Y', errors='coerce')
            )
            artist_df = artist_df.sort_values('Release Date')

        valid_features.append('popularity')

        return artist_df, valid_features, item_comparison_data
    return None, None, None

def get_artist_comparison_input_and_plot(artist_df, valid_features, item_data, item_comparison_data):
    if len(artist_df) > 0:
        artist_df['Release Year'] = artist_df['Release Date'].dt.year.astype('Int64') 
        artist_df['Album (Year)'] = artist_df.apply(
            lambda row: f"{row['Album'][:12]}.. ({row['Release Year']})" if pd.notna(row['Release Year']) and len(row['Album']) > 15
                        else f"{row['Album']} ({row['Release Year']})" if pd.notna(row['Release Year'])
                        else row['Album'],  
            axis=1
        )
        
        #heat albuns
        heatmap_features = ['acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence', 'popularity']
        filtered_df_1 = artist_df[artist_df['Artist ID'] == item_data['id']]
        heatmap_df_1 = (filtered_df_1.groupby(["Album (Year)"])[heatmap_features].mean().reindex(filtered_df_1['Album (Year)'].unique()))
        filtered_df_2 = artist_df[artist_df['Artist ID'] == item_comparison_data['id']]
        heatmap_df_2 = (filtered_df_2.groupby(["Album (Year)"])[heatmap_features].mean().reindex(filtered_df_2['Album (Year)'].unique()))
        
        # heatmap 1
        fig_1 = go.Figure(data=go.Heatmap(
            z=heatmap_df_1.round(3).T.values,
            x=heatmap_df_1.index.tolist(),
            y=heatmap_features,
            colorscale="RdBu_r", 
            showscale=False,
            text=heatmap_df_1.round(3).T.values, 
            texttemplate="%{text}",
            hovertemplate=
                "<b>%{x}</b><br>"  
                + "%{y}: %{z}<br>",  
                                ))

        fig_1.update_layout(
            title=f"{item_data['name']}",
            xaxis_visible=False,
            margin=dict(l=50, r=0, t=50, b=50)
        )

        # heatmap 2
        fig_2 = go.Figure(data=go.Heatmap(
            z=heatmap_df_2.round(3).T.values,
            x=heatmap_df_2.index.get_level_values("Album (Year)").tolist(),
            y=heatmap_features,
            colorscale="RdBu_r", 
            text=heatmap_df_2.round(3).T.values, 
            texttemplate="%{text}",
            hovertemplate=
                "<b>%{x}</b><br>"  
                + "%{y}: %{z}<br>",  
        ))

        fig_2.update_layout(
            title=f"{item_comparison_data['name']}",
            yaxis_visible=False,
            xaxis_visible=False,
            margin=dict(l=25, r=50, t=50, b=50)
        )
        
        col3, col4 = st.columns(2)
        with col3:
            st.plotly_chart(fig_1, use_container_width=True)
        with col4:
            st.plotly_chart(fig_2, use_container_width=True)

        #polar chart
        grouped_df = artist_df.groupby("Artist Number").agg(
                                                        artist_name=("Artist", "first"),
                                                        # artist_number=("Artist Number", "first"),
                                                        popularity=("popularity", "mean"),
                                                        acousticness=("acousticness", "mean"), 
                                                        danceability=("danceability", "mean"), 
                                                        energy=("energy", "mean"),
                                                        instrumentalness=("instrumentalness", "mean"), 
                                                        liveness=("liveness", "mean"),
                                                        speechiness=("speechiness", "mean"), 
                                                        valence=("valence", "mean") 
                                                        ).reset_index()
        df_long = grouped_df.melt(id_vars=['Artist Number', 'artist_name'], var_name='feature', value_name='value')
        fig_polar = px.line_polar(df_long, r='value', theta='feature', color='artist_name', line_close=True, template="plotly_dark")
        fig_polar.update_layout(title = 'Polar Chart - Average Features',legend=dict(orientation="h"), height = 700, font_size = 16, autosize=True) 
        st.plotly_chart(fig_polar, use_container_width=True)

        #tsne
        features_dimensionality = ['acousticness', 'danceability', 'energy','instrumentalness', 'liveness', 'speechiness', 'valence', 'tempo']
        feature_data = artist_df[features_dimensionality]

        scaler_album_features = StandardScaler()
        scaled_data = scaler_album_features.fit_transform(feature_data)

        tsne = TSNE(n_components=2, perplexity=max(1, min(30, len(feature_data)//10)), random_state=42)
        tsne_embedding = tsne.fit_transform(scaled_data)
        tsne_df = pd.DataFrame(tsne_embedding, columns=['x', 'y'])
        tsne_df['Album'] = artist_df['Album']
        tsne_df['Track'] = artist_df['Track']
        tsne_df['Artist'] = artist_df['Artist']

        fig_tsne = px.scatter(
            tsne_df, 
            x='x', 
            y='y', 
            hover_data=['Album', 'Track', 'Artist'], 
            color = 'Artist',
            symbol = 'Album',
            template="plotly_dark"
        )

        fig_tsne.update_layout(
            title="t-SNE Visualization of Artists Discography",
            xaxis=dict(
                showgrid=True,
                showticklabels=False,
            ),
            yaxis=dict(
                showgrid=True,
                showticklabels=False,
            ),
        )

        st.plotly_chart(fig_tsne)

        #plots by feature
        feature = st.selectbox("Select an attribute to plot:", valid_features)
        
        #boxplot
        fig_boxplot = px.box(artist_df, 
                        x="Album (Year)", 
                        y=feature, 
                        color="Artist", 
                        color_discrete_sequence=px.colors.qualitative.G10,
                        category_orders={"Album (Year)": list(artist_df["Album (Year)"].unique())},
                        custom_data=["Album"]
                        )

        fig_boxplot.update_layout(
            title = f"{feature.capitalize()} per album over time - Boxplot",
            yaxis_title=feature.capitalize(),
            xaxis_title=None,
            legend=dict(orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                        )

        )

        artist_1_avg = filtered_df_1.groupby("Album (Year)")[feature].mean().reset_index()
        artist_1_avg = artist_1_avg.merge(artist_df[['Album (Year)', 'Release Date']].drop_duplicates(), on="Album (Year)")
        artist_1_avg = artist_1_avg.sort_values(by='Release Date')
        artist_2_avg = filtered_df_2.groupby("Album (Year)")[feature].mean().reset_index()
        artist_2_avg = artist_2_avg.merge(artist_df[['Album (Year)', 'Release Date']].drop_duplicates(), on="Album (Year)")
        artist_2_avg = artist_2_avg.sort_values(by='Release Date')

        fig_line = go.Figure()

        fig_line.update_layout(
            title = f"{feature.capitalize()} per album over time - Line",
            yaxis_title=feature.capitalize(),
            xaxis_title=None,
            legend=dict(orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                        ),
            xaxis=dict(categoryorder='array',
                       categoryarray=artist_df['Album (Year)'].tolist(),
                       showgrid=True),
        )

        fig_line.add_trace(go.Scatter(
            x=artist_1_avg["Album (Year)"],  
            y=artist_1_avg[feature],  
            mode="lines+markers",  
            name=f"Average {feature.capitalize()} - {item_data['name']}",  
            line=dict(color="blue", width=2),  
        ))

        fig_line.add_trace(go.Scatter(
            x=artist_2_avg["Album (Year)"],  
            y=artist_2_avg[feature],  
            mode="lines+markers",  
            name=f"Average {feature.capitalize()} - {item_comparison_data['name']}",  
            line=dict(color="red", width=2),  
        ))

        
        #violin
        fig_violin = px.violin(artist_df, 
                    x="Album (Year)", 
                    y=feature, 
                    color="Artist", 
                    color_discrete_sequence=px.colors.qualitative.G10,
                    category_orders={"Album (Year)": list(artist_df["Album (Year)"].unique())},
                    points="all", 
                    violinmode='overlay',
                    custom_data=["Album", "Track"]

                )
        
        fig_violin.update_layout(
            title = f"{feature.capitalize()} per album over time - Violin",
            yaxis_title=feature.capitalize(),
            xaxis_title=None,
            legend=dict(orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                        )

        )

        fig_violin.update_traces(hovertemplate=(
                        "<b>Album:</b> %{customdata[0]}<br>" 
                        "<b>Track:</b> %{customdata[1]}<br>"  
                        "<b>Value:</b> %{y}<br>" 
                    )
                )
        
        #plot charts
        tabs = st.tabs(["Violin", "Boxplot", "Line"])

        with tabs[0]:
            st.plotly_chart(fig_violin)

        with tabs[1]:
            st.plotly_chart(fig_boxplot)

        with tabs[2]:
            st.plotly_chart(fig_line)

        st.text("Source Data:")
        st.dataframe(artist_df[['Artist','Album', 'Release Date', 'Track', 'acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence', 'loudness', 'tempo', 'duration_ms']])


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
        item_comparison_data = item_comparison()
        artist_df, valid_features, item_comparison_data = artist_comparison(item_data, item_comparison_data)
        if item_comparison_data is not None:
            get_artist_comparison_input_and_plot(artist_df, valid_features, item_data, item_comparison_data)