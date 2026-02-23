import os
import uuid
from datetime import datetime, date

import pandas as pd
import streamlit as st

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

앱이름 = "🌱 매현중 스마트 가든"

시트_학생명단 = "학생명단"
시트_기록 = "기록"
시트_공지 = "공지사항"

날씨목록 = ["☀️ 맑음", "⛅ 흐림", "🌧 비", "❄️ 눈", "🌬 바람"]
활동목록 = ["물주기", "잡초제거", "관찰", "정리", "비료/퇴비", "기록정리", "기타"]

def 구글연결():
    import gspread
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    서비스정보 = st.secrets["google_service_account"]
    시트ID = st.secrets["GOOGLE_SHEET_ID"]
    폴더ID = st.secrets["DRIVE_FOLDER_ID"]

    범위 = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    인증 = Credentials.from_service_account_info(서비스정보, scopes=범위)

    gc = gspread.authorize(인증)
    시트 = gc.open_by_key(시트ID)
    드라이브 = build("drive", "v3", credentials=인증)

    return 시트, 드라이브, 폴더ID

@st.cache_data(ttl=30)
def 학생명단불러오기():
    시트, _, _ = 구글연결()
    ws = 시트.worksheet(시트_학생명단)
    데이터 = ws.get_all_records()
    df = pd.DataFrame(데이터)
    if df.empty:
        return pd.DataFrame(columns=["학번","이름"])
    df["학번"] = df["학번"].astype(str).str.strip()
    df["이름"] = df["이름"].astype(str).str.strip()
    return df


def 기록불러오기():
    시트, _, _ = 구글연결()
    ws = 시트.worksheet(시트_기록)
    데이터 = ws.get_all_records()
    df = pd.DataFrame(데이터)
    if df.empty:
        return pd.DataFrame()
    return df


def 기록추가(행):
    시트, _, _ = 구글연결()
    ws = 시트.worksheet(시트_기록)
    헤더 = ws.row_values(1)
    ws.append_row([행.get(h,"") for h in 헤더])


def 사진업로드(파일):
    시트, 드라이브, 폴더ID = 구글연결()
    파일바이트 = 파일.getbuffer()
    미디어 = MediaIoBaseUpload(io.BytesIO(파일바이트), mimetype=파일.type)

    새이름 = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{파일.name}"
    메타 = {"name": 새이름, "parents": [폴더ID]}

    생성 = 드라이브.files().create(body=메타, media_body=미디어, fields="id, webViewLink").execute()
    파일ID = 생성["id"]

    드라이브.permissions().create(
        fileId=파일ID,
        body={"type": "anyone", "role": "reader"}
    ).execute()

    return 생성.get("webViewLink", f"https://drive.google.com/file/d/{파일ID}/view")


# ================= UI =================

st.set_page_config(page_title=앱이름, page_icon="🌱")
st.title(앱이름)

# 로그인
if "로그인" not in st.session_state:
    st.session_state["로그인"] = False

if not st.session_state["로그인"]:
    st.subheader("🔐 학생 로그인")
    with st.form("로그인폼"):
        학번 = st.text_input("학번")
        이름 = st.text_input("이름")
        로그인버튼 = st.form_submit_button("로그인")
    if 로그인버튼:
        df = 학생명단불러오기()
        확인 = df[(df["학번"]==학번) & (df["이름"]==이름)]
        if 확인.empty:
            st.error("학번 또는 이름이 올바르지 않습니다.")
        else:
            st.session_state["로그인"] = True
            st.session_state["학번"] = 학번
            st.session_state["이름"] = 이름
            st.rerun()
    st.stop()

학번 = st.session_state["학번"]
이름 = st.session_state["이름"]

메뉴 = st.sidebar.radio("메뉴", ["📸 기록하기","📖 기록보기"])

if 메뉴 == "📸 기록하기":
    st.subheader("오늘 기록하기")

    with st.form("기록폼"):
        반 = st.text_input("반 (예: 1-3)")
        모둠 = st.text_input("모둠")
        날짜 = st.date_input("활동날짜", value=date.today()).strftime("%Y-%m-%d")
        식물 = st.text_input("재배식물")
        날씨 = st.selectbox("날씨", 날씨목록)
        사진 = st.file_uploader("사진 업로드", type=["jpg","png","jpeg"])
        활동 = st.multiselect("오늘활동", 활동목록)
        키 = st.number_input("식물키(cm)", 0.0, 300.0)
        잎 = st.number_input("잎개수", 0)
        관찰 = st.text_area("관찰내용")
        성장 = st.text_area("나의성장")
        저장 = st.form_submit_button("저장하기")

    if 저장:
        if 사진 is None:
            st.error("사진은 필수입니다.")
        else:
            링크 = 사진업로드(사진)
            행 = {
                "기록ID": str(uuid.uuid4())[:8],
                "저장시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "활동날짜": 날짜,
                "학번": 학번,
                "기록자": 이름,
                "반": 반,
                "모둠": 모둠,
                "재배식물": 식물,
                "날씨": 날씨,
                "오늘활동": ", ".join(활동),
                "식물키(cm)": 키,
                "잎개수": 잎,
                "관찰내용": 관찰,
                "나의성장": 성장,
                "사진링크": 링크,
                "교사댓글": ""
            }
            기록추가(행)
            st.success("저장 완료!")

if 메뉴 == "📖 기록보기":
    st.subheader("기록보기")
    df = 기록불러오기()
    if df.empty:
        st.info("기록이 없습니다.")
    else:
        st.dataframe(df[["활동날짜","기록자","재배식물","교사댓글"]])