import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import plotly.express as px
import plotly.graph_objects as go

import pandas as pd
import streamlit as st
from config import CLIENT_ID, CLIENT_SECRET
import requests

st.header('Music Analytics App')

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=st.secrets['CLIENT_ID'],client_secret=st.secrets['CLIENT_SECRET']))

# def save_album_image(img_url, track_id):
#     r = requests.get(img_url)
#     file_path = f'app/img/{track_id}.jpg'
#     with open(file_path, "wb") as file:
#         file.write(r.content)    
#     return file_path

search_choices = ['Song', 'Album', 'Artist/Band']
search_selected = st.sidebar.selectbox("Search by: ", search_choices)
search_keyword = st.text_input("Which " + search_selected.lower() + " do you have in mind?")

params = {
    'Song': {'search_by': "track", 'search_results': "{} - {}", 'item_choices': ['Song Features', 'Song Comparison']},
    'Album': {'search_by': 'album', 'search_results': "{} - {} ({})", 'item_choices': ['Album Features', 'TestAlbum']},
    'Artist/Band': {'search_by': 'artist', 'search_results': "{}", 'item_choices': ['Artist/Band Features', 'TestArtist']}
}

def collect_input(search_keyword):
    items = sp.search(q=search_keyword,type=params[search_selected]['search_by'], limit=20)
    # items = sp.search(q=f'{params[search_selected]['search_by']}:'+ search_keyword,type=params[search_selected]['search_by'], limit=20)
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

    # image_path = save_album_image(item_data['album']['images'][1]['url'], item_id)
    st.subheader(f"Album/EP: {track_data['album']['name']} ({track_data['album']['release_date'][:4]})")
    # st.image(image_path, caption=f"Track ID: {item_id}", use_container_width=True)
    st.image(item_data['album']['images'][1]['url'], use_container_width=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Popularity (0-100)", track_data['popularity'])
        st.metric("Loudness", df.iloc[0]['loudness'])
    with col2:
        st.metric("Tempo (bpm)", df.iloc[0]['tempo'])
        st.metric("Key (0-11)", df.iloc[0]['key'])
    with col3:
        st.metric("Duration (s)", track_data['duration_ms']/1000)
        st.metric("Mode", df.iloc[0]['mode'])

    fig = px.line_polar(df_features, r=df_features.iloc[0].tolist(), theta=valid_features, line_close=True,
                        markers=True,
                        color_discrete_sequence=px.colors.sequential.Plasma_r,
                        template="plotly_dark")
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
        df_features['name'] = combined_df['name'].apply(lambda x: x[:15] + "..." if len(x) > 15 else x)

        # image_path_1 = save_album_image(item_data['album']['images'][1]['url'], item_id_1)
        # image_path_2 = save_album_image(item_comparison_data['album']['images'][1]['url'], item_id_2)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader(f"Album/EP: {track_data_1['album']['name']} ({track_data_1['album']['release_date'][:4]})")
            st.image(item_data['album']['images'][1]['url'], caption=f"Track ID: {item_id_1}", use_container_width=True)
        with col2:
            st.subheader(f"Album/EP: {track_data_2['album']['name']} ({track_data_2['album']['release_date'][:4]})")
            st.image(item_comparison_data['album']['images'][1]['url'], caption=f"Track ID: {item_id_2}", use_container_width=True)


        df_long = df_features.melt(id_vars='name', var_name='feature', value_name='value')
        fig = px.line_polar(df_long, r='value', theta='feature', color='name', line_close=True, template="plotly_dark")

        st.plotly_chart(fig)
        st.dataframe(df_features, hide_index=True, use_container_width=True)

def album_features(item_data):
    album_id = item_data['id']

    album_tracks = sp.album_tracks(album_id)

    track_data = []
    for track in album_tracks['items']:
        track_data.append({
            'track_id': track['id'],
            'track_name': track['name'],
            'track_number': track['track_number']
        })

    df_tracks = pd.DataFrame(track_data)

    track_ids = df_tracks['track_id'].tolist()
    audio_features = sp.audio_features(track_ids)
    valid_features = ['acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence']

    for feature in valid_features:
        df_tracks[feature] = [track[feature] if track else None for track in audio_features]

    df_tracks['track_label'] = df_tracks['track_number'].astype(str) + ". " + df_tracks['track_name']

    df_tracks = df_tracks.set_index('track_number')

    df_features = df_tracks[valid_features].round(3).T

    fig = px.imshow(df_features,
                    color_continuous_scale='RdBu_r',
                    text_auto=True,
                    )    
    

    fig.update_layout(xaxis_title ='Song/Track',
                      xaxis = dict(tickmode='linear'),                    
                      title = 'Album Features Heatmap'
                      )
    
    # fig.update(data=[{'customdata': df_tracks[['track_label']],
    # 'hovertemplate': 'Letter: %{x}<br>Nickname: %{y}<br>Fullname: %{customdata}<br>Color: %{customdata[0]}<extra></extra>'}])
    
    # fig.update_traces(hoverinfo = 'text+y+x+z',
    #                 #   customdata=df_tracks[['track_label']],
    #                 #   hovertemplate='GDP: %{customdata[0]} <br>Life Expectancy: test %{customdata}, %{x}, %{y}'
    #                   )




    st.plotly_chart(fig, use_container_width=True)
    print_features = ['track_label','acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence']
    df_print = df_tracks[print_features]
    st.dataframe(df_print, hide_index=True, use_container_width=True)


selected_analysis = None
item_data = None

# if search_keyword is not None and len(str(search_keyword)) > 0:
#     selected_analysis, item_data = analysis_choice_workflow()


if search_keyword is not None and len(str(search_keyword)) > 0:
    selected_analysis, item_data = collect_analysis_info()

if selected_analysis == 'Song Features':
    song_features(item_data)
elif selected_analysis == 'Song Comparison':
    song_comparison(item_data)
elif selected_analysis == 'Album Features':
    album_features(item_data)


    
##original 

def original_code():
    search_results = []

    if search_keyword is not None and len(str(search_keyword)) > 0:
        if search_selected == 'Song':
            track_id = None
            tracks = sp.search(q='track:'+ search_keyword,type='track', limit=10)
            tracks_list = tracks['tracks']['items']

            for track in tracks_list:
                search_results.append(track['name'] + " - " + track['artists'][0]['name'])
            
            selected_track = st.selectbox(f"Select your {search_selected}: ", search_results)

            for track in tracks_list:
                str_temp = track['name'] + " - " + track['artists'][0]['name']
                if str_temp == selected_track:
                    track_id = track['id']
                    image_url = track['album']['images'][1]['url']
                
            # selected_track_choice = None   
            if track_id is not None:
                track_choices = ['Features', 'Comparison']
                selected_track_choice = st.sidebar.selectbox('Select your action: ', track_choices)        
                if selected_track_choice == 'Features':
                    track_features  = sp.audio_features(track_id) 
                    track_data = sp.track(track_id)
                    df = pd.DataFrame(track_features, index=[0])
                    valid_features = ['acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'speechiness', 'valence']
                    df_features = df[valid_features]

                    image_path = save_album_image(image_url, track_id)
                    st.subheader(f"Album: {track_data['album']['name']} ({track_data['album']['release_date'][:4]})")
                    st.image(image_path, caption=f"Track ID: {track_id}", use_container_width=True)

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Popularity (0-100)", track_data['popularity'])
                        st.metric("Loudness", df.iloc[0]['loudness'])
                    with col2:
                        st.metric("Tempo (bpm)", df.iloc[0]['tempo'])
                        st.metric("Key (0-11)", df.iloc[0]['key'])
                    with col3:
                        st.metric("Duration (s)", track_data['duration_ms']/1000)
                        st.metric("Mode", df.iloc[0]['mode'])

                    fig = px.line_polar(df_features, r=df_features.iloc[0].tolist(), theta=valid_features, line_close=True,
                                        markers=True,
                                        color_discrete_sequence=px.colors.sequential.Plasma_r,
                                        template="plotly_dark")
                    fig.update_traces(fill='toself')
                    st.plotly_chart(fig)
                    st.dataframe(df_features, hide_index=True, use_container_width=True)
                
        elif search_selected == 'Album':
            pass
        elif search_selected == 'Artist/Band':
            pass
        