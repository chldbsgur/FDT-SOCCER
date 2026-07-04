import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(
    page_title="축구 압박 및 수비 효과 분석 대시보드",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚽ 축구 전술 데이터 분석 대시보드")
st.markdown("요청하신 **수비 성공률 기준 시각화 변경, 실점/간접 비고 데이터 정밀 매핑 기능**이 완벽하게 추가되었습니다.")

# 2. 사이드바 - 파일 업로드 및 필터
st.sidebar.header("📁 데이터 로드 및 설정")
uploaded_files = st.sidebar.file_uploader(
    "엑셀(.xlsx) 또는 CSV(.csv) 파일을 선택하세요 (다중 선택 가능)",
    type=["xlsx", "csv"],
    accept_multiple_files=True
)

@st.cache_data
def load_and_combine_data(files):
    all_dfs = []
    for f in files:
        try:
            if f.name.endswith('.csv'):
                df_single = pd.read_csv(f)
            else:
                df_single = pd.read_excel(f)
            df_single['출처파일'] = f.name
            all_dfs.append(df_single)
        except Exception as e:
            st.sidebar.error(f"{f.name} 파일 읽기 오류: {e}")
    
    if not all_dfs:
        return pd.DataFrame()
    
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # 데이터 표준화 및 전처리
    for col in ['team', 'situation', 'type', 'pushing on', 'O/X', 'defend', '비고']:
        if col in combined_df.columns:
            combined_df[col] = combined_df[col].astype(str).str.strip()
            if col != '비고':
                combined_df[col] = combined_df[col].str.upper()
            
    # 데이터 결함 보정 로직 (O/X와 defend 중 하나만 차있을 경우 복사)
    is_ox_valid = combined_df['O/X'].isin(['O', 'X'])
    is_def_valid = combined_df['defend'].isin(['O', 'X'])
    
    mask_copy_to_def = is_ox_valid & ~is_def_valid
    combined_df.loc[mask_copy_to_def, 'defend'] = combined_df.loc[mask_copy_to_def, 'O/X']
    
    mask_copy_to_ox = ~is_ox_valid & is_def_valid
    combined_df.loc[mask_copy_to_ox, 'O/X'] = combined_df.loc[mask_copy_to_ox, 'defend']
            
    return combined_df

# 핵심 연산 함수 정의
def compute_pressing_metrics(df_input):
    total_push = df_input['pushing on'].isin(['O', 'X']).sum()
    push_o = (df_input['pushing on'] == 'O').sum()
    push_x = (df_input['pushing on'] == 'X').sum()
    
    push_o_pct = (push_o / total_push * 100) if total_push > 0 else 0
    push_x_pct = (push_x / total_push * 100) if total_push > 0 else 0
    
    df_o = df_input[df_input['pushing on'] == 'O']
    total_ox = df_o['O/X'].isin(['O', 'X']).sum()
    ox_o = (df_o['O/X'] == 'O').sum()
    ox_x = (df_o['O/X'] == 'X').sum()
    
    ox_o_pct = (ox_o / total_ox * 100) if total_ox > 0 else 0
    ox_x_pct = (ox_x / total_ox * 100) if total_ox > 0 else 0
    
    total_def_o = df_o['defend'].isin(['O', 'X']).sum()
    def_o_o = (df_o['defend'] == 'O').sum()
    def_o_x = (df_o['defend'] == 'X').sum()
    
    def_o_o_pct = (def_o_o / total_def_o * 100) if total_def_o > 0 else 0
    def_o_x_pct = (def_o_x / total_def_o * 100) if total_def_o > 0 else 0
    
    df_x = df_input[df_input['pushing on'] == 'X']
    total_def_x = df_x['defend'].isin(['O', 'X']).sum()
    def_x_o = (df_x['defend'] == 'O').sum()
    def_x_x = (df_x['defend'] == 'X').sum()
    
    def_x_o_pct = (def_x_o / total_def_x * 100) if total_def_x > 0 else 0
    def_x_x_pct = (def_x_x / total_def_x * 100) if total_def_x > 0 else 0
    
    return {
        '총상황수': total_push,
        '시도횟수': push_o,
        '미시도횟수': push_x,
        '시도비율(%)': round(push_o_pct, 1),
        '미시도비율(%)': round(push_x_pct, 1),
        '시도시_성공률(%)': round(ox_o_pct, 1),
        '시도시_실패율(%)': round(ox_x_pct, 1),
        '시도시_수비성공률(%)': round(def_o_o_pct, 1),
        '미시도시_수비성공률(%)': round(def_x_o_pct, 1),
        '시도시_수비실패율(%)': round(def_o_x_pct, 1),
        '미시도시_수비실패율(%)': round(def_x_x_pct, 1)
    }

if uploaded_files:
    raw_df = load_and_combine_data(uploaded_files)
    
    if not raw_df.empty:
        st.sidebar.subheader("🔍 데이터 필터")
        teams = [t for t in raw_df['team'].unique().tolist() if t not in ['NAN', 'nan', '']]
        selected_teams = st.sidebar.multiselect("분석할 팀 선택", teams, default=teams)
        
        filtered_df = raw_df[raw_df['team'].isin(selected_teams)].copy()
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 1. 전체 지표 분석", 
            "📂 2. Situation별 세부 분석", 
            "⚡ 3. Type별 세부 분석", 
            "📋 4. 결합 원본 데이터"
        ])
        
        # --- TAB 1: 전체 지표 분석 ---
        with tab1:
            st.subheader("📋 전방 압박(Pushing On) 및 수비 연계 전체 요약 (보정 데이터 적용)")
            overall = compute_pressing_metrics(filtered_df)
            
            # KPI (수비 실패율 -> 수비 성공률로 변경)
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("전체 분석 상황 수", f"{overall['총상황수']} 건")
            kpi2.metric("Pushing On 시도율", f"{overall['시도비율(%)']} %", f"{overall['시도횟수']}회 시도")
            kpi3.metric("압박 시도 시 성공률", f"{overall['시도시_성공률(%)']} %")
            kpi4.metric("미시도 시 수비 성공률", f"{overall['미시도시_수비성공률(%)']} %") 
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                fig_attempt = go.Figure(data=[go.Pie(
                    labels=['시도 (O)', '미시도 (X)'],
                    values=[overall['시도횟수'], overall['미시도횟수']],
                    hole=.4,
                    marker=dict(colors=['#3498DB', '#95A5A6']),
                    textinfo='label+percent'
                )])
                fig_attempt.update_layout(title_text="<b>전체 Pushing On 시도 vs 미시도 비율</b>")
                st.plotly_chart(fig_attempt, use_container_width=True)
                
            with col2:
                fig_success = go.Figure(data=[go.Pie(
                    labels=['압박 성공 (O)', '압박 실패 (X)'],
                    values=[overall['시도시_성공률(%)'], overall['시도시_실패율(%)']],
                    hole=.4,
                    marker=dict(colors=['#2ECC71', '#E74C3C']),
                    textinfo='label+percent'
                )])
                fig_success.update_layout(title_text="<b>압박 시도 시 성공률 vs 실패율</b>")
                st.plotly_chart(fig_success, use_container_width=True)
            
            st.markdown("---")
            st.subheader("🛡️ 압박 시도 여부에 따른 수비 성과 정밀 비교 (실점/간접 비고 포함)")
            
            # [수정사항] 실점/간접 카운트 정밀 연산 로직
            valid_def_o = filtered_df[(filtered_df['pushing on'] == 'O') & filtered_df['defend'].isin(['O', 'X'])]
            tot_o = len(valid_def_o)
            pct_o_gan = len(valid_def_o[valid_def_o['비고'] == '간접']) / tot_o * 100 if tot_o else 0
            pct_o_sil = len(valid_def_o[valid_def_o['비고'] == '실점']) / tot_o * 100 if tot_o else 0
            pct_o_succ = len(valid_def_o[(valid_def_o['defend'] == 'O') & (valid_def_o['비고'] != '간접')]) / tot_o * 100 if tot_o else 0
            pct_o_fail = len(valid_def_o[(valid_def_o['defend'] == 'X') & (valid_def_o['비고'] != '실점')]) / tot_o * 100 if tot_o else 0
            
            valid_def_x = filtered_df[(filtered_df['pushing on'] == 'X') & filtered_df['defend'].isin(['O', 'X'])]
            tot_x = len(valid_def_x)
            pct_x_gan = len(valid_def_x[valid_def_x['비고'] == '간접']) / tot_x * 100 if tot_x else 0
            pct_x_sil = len(valid_def_x[valid_def_x['비고'] == '실점']) / tot_x * 100 if tot_x else 0
            pct_x_succ = len(valid_def_x[(valid_def_x['defend'] == 'O') & (valid_def_x['비고'] != '간접')]) / tot_x * 100 if tot_x else 0
            pct_x_fail = len(valid_def_x[(valid_def_x['defend'] == 'X') & (valid_def_x['비고'] != '실점')]) / tot_x * 100 if tot_x else 0
            
            defend_comp = pd.DataFrame({
                '압박 시도 여부': [
                    '압박 시도 시 (Pushing O)', '압박 시도 시 (Pushing O)', '압박 시도 시 (Pushing O)', '압박 시도 시 (Pushing O)',
                    '압박 미시도 시 (Pushing X)', '압박 미시도 시 (Pushing X)', '압박 미시도 시 (Pushing X)', '압박 미시도 시 (Pushing X)'
                ],
                '수비 결과': [
                    '수비 성공 (O)', '간접 성공', '수비 실패 (X)', '실점',
                    '수비 성공 (O)', '간접 성공', '수비 실패 (X)', '실점'
                ],
                '비율(%)': [
                    pct_o_succ, pct_o_gan, pct_o_fail, pct_o_sil,
                    pct_x_succ, pct_x_gan, pct_x_fail, pct_x_sil
                ]
            })
            
            # [수정사항] 실점은 실패와 같은 빨강, 간접 성공은 성공과 같은 초록색 매핑
            color_map_defend = {
                '수비 성공 (O)': '#27AE60',  # 초록
                '간접 성공': '#27AE60',      # 동일한 초록
                '수비 실패 (X)': '#C0392B',  # 빨강
                '실점': '#C0392B'            # 동일한 빨강
            }
            
            fig_defend = px.bar(
                defend_comp, x='압박 시도 여부', y='비율(%)', color='수비 결과', barmode='group',
                text_auto='.1f', color_discrete_map=color_map_defend
            )
            fig_defend.update_layout(title_text="<b>압박 시도 여부에 따른 수비 연계 성공/실패 (특이사항 분리)</b>")
            fig_defend.update_yaxes(range=[0, 100])
            st.plotly_chart(fig_defend, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📝 특이사항(비고) 분석 - '간접' 발생 비중 및 '실점' 기록")
            
            total_rows = len(filtered_df)
            ganjeob_count = (filtered_df['비고'] == '간접').sum()
            ganjeob_pct = (ganjeob_count / total_rows * 100) if total_rows > 0 else 0
            
            df_siljeom = filtered_df[filtered_df['비고'] == '실점']
            
            col_rem1, col_rem2 = st.columns([1, 3])
            with col_rem1:
                st.markdown("<br><br>", unsafe_allow_html=True)
                st.metric(label="📌 전체 로그 중 '간접' 발생 비율", value=f"{ganjeob_pct:.1f} %", delta=f"총 {ganjeob_count}건 발생")
                
            with col_rem2:
                st.markdown(f"🚨 **실점 상황 목록 요약 (총 {len(df_siljeom)}건)**")
                if not df_siljeom.empty:
                    st.dataframe(df_siljeom[['출처파일', 'half', 'min', 'sec', 'team', 'number', 'situation', 'type', 'pushing on', 'O/X', 'defend']], use_container_width=True)
                else:
                    st.info("현재 필터링된 범위 내에 '실점'으로 기록된 상황이 존재하지 않습니다.")
                
        # --- TAB 2: Situation별 분석 ---
        with tab2:
            st.subheader("📂 전술 상황(Situation)별 가독성 높은 입체 분석")
            
            sit_list = []
            for sit, group in filtered_df.groupby('situation'):
                if sit in ['NAN', 'nan', ''] or pd.isna(sit):
                    continue
                metrics = compute_pressing_metrics(group)
                metrics['Situation'] = sit
                sit_list.append(metrics)
                
            if sit_list:
                df_sit = pd.DataFrame(sit_list)
                # 수비 성공률을 전진 배치
                col_order = [
                    'Situation', '총상황수', '시도비율(%)', '미시도비율(%)', 
                    '시도시_성공률(%)', '시도시_실패율(%)', 
                    '시도시_수비성공률(%)', '미시도시_수비성공률(%)', '시도시_수비실패율(%)', '미시도시_수비실패율(%)'
                ]
                df_sit = df_sit[col_order]
                
                st.markdown("##### 📊 Situation별 모든 지표 종합 테이블")
                st.dataframe(
                    df_sit.style.background_gradient(cmap="Blues", subset=['시도비율(%)', '시도시_성공률(%)', '시도시_수비성공률(%)', '미시도시_수비성공률(%)'])
                    .background_gradient(cmap="Reds", subset=['시도시_실패율(%)', '시도시_수비실패율(%)', '미시도시_수비실패율(%)']),
                    use_container_width=True
                )
                
                st.markdown("---")
                sit_col1, sit_col2 = st.columns(2)
                
                with sit_col1:
                    df_sit_melt1 = df_sit.melt(id_vars='Situation', value_vars=['시도비율(%)', '미시도비율(%)'], var_name='구분', value_name='비율(%)')
                    fig_sit_attempt = px.bar(
                        df_sit_melt1, x='Situation', y='비율(%)', color='구분', barmode='stack',
                        title="<b>Situation별 Pushing On 시도 vs 미시도 비중 (%)</b>", text_auto='.1f',
                        color_discrete_sequence=['#2C3E50', '#BDC3C7']
                    )
                    fig_sit_attempt.update_yaxes(range=[0, 100])
                    st.plotly_chart(fig_sit_attempt, use_container_width=True)
                    
                with sit_col2:
                    df_sit_melt2 = df_sit.melt(id_vars='Situation', value_vars=['시도시_성공률(%)', '시도시_실패율(%)'], var_name='압박결과', value_name='비율(%)')
                    fig_sit_ox = px.bar(
                        df_sit_melt2, x='Situation', y='비율(%)', color='압박결과', barmode='group',
                        title="<b>Situation별 압박 시도 성공률 vs 실패율</b>", text_auto='.1f',
                        color_discrete_sequence=['#2ECC71', '#E74C3C']
                    )
                    fig_sit_ox.update_yaxes(range=[0, 100])
                    st.plotly_chart(fig_sit_ox, use_container_width=True)
                
                st.markdown("---")
                # [수정사항] 실패율 차트를 수비 성공률 차트로 100% 교체
                st.markdown("##### 🛡️ Situation별 수비 성공률 지표 비교 (시도 시 vs 미시도 시)")
                
                df_sit_melt3 = df_sit.melt(id_vars='Situation', value_vars=['시도시_수비성공률(%)', '미시도시_수비성공률(%)'], 
                                           var_name='수비 성공 조건', value_name='성공률(%)')
                fig_sit_defend = px.bar(
                    df_sit_melt3, x='Situation', y='성공률(%)', color='수비 성공 조건', barmode='group',
                    title="<b>Situation별 수비 성공률 비교 (압박 시도 시 vs 압박 미시도 시)</b>", text_auto='.1f',
                    color_discrete_sequence=['#27AE60', '#2980B9'] # 성공을 상징하는 밝은톤의 초록과 파랑 계열
                )
                fig_sit_defend.update_yaxes(range=[0, 100])
                st.plotly_chart(fig_sit_defend, use_container_width=True)
            else:
                st.warning("분석할 유효한 Situation 데이터가 존재하지 않습니다.")
                
        # --- TAB 3: Type별 세부 분석 ---
        with tab3:
            st.subheader("⚡ 전술 타입(Type)별 가독성 높은 입체 분석")
            
            type_list = []
            for t_val, group in filtered_df.groupby('type'):
                if t_val in ['NAN', 'nan', ''] or pd.isna(t_val):
                    continue
                metrics = compute_pressing_metrics(group)
                metrics['Type'] = t_val
                type_list.append(metrics)
                
            if type_list:
                df_type = pd.DataFrame(type_list)
                col_order_type = [
                    'Type', '총상황수', '시도비율(%)', '미시도비율(%)', 
                    '시도시_성공률(%)', '시도시_실패율(%)', 
                    '시도시_수비성공률(%)', '미시도시_수비성공률(%)', '시도시_수비실패율(%)', '미시도시_수비실패율(%)'
                ]
                df_type = df_type[col_order_type]
                
                st.markdown("##### 📊 Type별 모든 지표 종합 테이블")
                st.dataframe(
                    df_type.style.background_gradient(cmap="Blues", subset=['시도비율(%)', '시도시_성공률(%)', '시도시_수비성공률(%)', '미시도시_수비성공률(%)'])
                    .background_gradient(cmap="Reds", subset=['시도시_실패율(%)', '시도시_수비실패율(%)', '미시도시_수비실패율(%)']),
                    use_container_width=True
                )
                
                st.markdown("---")
                type_col1, type_col2 = st.columns(2)
                
                with type_col1:
                    df_type_melt1 = df_type.melt(id_vars='Type', value_vars=['시도비율(%)', '미시도비율(%)'], var_name='구분', value_name='비율(%)')
                    fig_type_attempt = px.bar(
                        df_type_melt1, x='Type', y='비율(%)', color='구분', barmode='stack',
                        title="<b>Type별 Pushing On 시도 vs 미시도 비중 (%)</b>", text_auto='.1f',
                        color_discrete_sequence=['#1ABC9C', '#BDC3C7']
                    )
                    fig_type_attempt.update_yaxes(range=[0, 100])
                    st.plotly_chart(fig_type_attempt, use_container_width=True)
                    
                with type_col2:
                    df_type_melt2 = df_type.melt(id_vars='Type', value_vars=['시도시_성공률(%)', '시도시_실패율(%)'], var_name='압박결과', value_name='비율(%)')
                    fig_type_ox = px.bar(
                        df_type_melt2, x='Type', y='비율(%)', color='압박결과', barmode='group',
                        title="<b>Type별 압박 시도 성공률 vs 실패율</b>", text_auto='.1f',
                        color_discrete_sequence=['#2ECC71', '#E74C3C']
                    )
                    fig_type_ox.update_yaxes(range=[0, 100])
                    st.plotly_chart(fig_type_ox, use_container_width=True)
                
                st.markdown("---")
                st.markdown("##### 🛡️ Type별 수비 성공률 지표 비교 (시도 시 vs 미시도 시)")
                
                df_type_melt3 = df_type.melt(id_vars='Type', value_vars=['시도시_수비성공률(%)', '미시도시_수비성공률(%)'], 
                                           var_name='수비 성공 조건', value_name='성공률(%)')
                fig_type_defend = px.bar(
                    df_type_melt3, x='Type', y='성공률(%)', color='수비 성공 조건', barmode='group',
                    title="<b>Type별 수비 성공률 비교 (압박 시도 시 vs 압박 미시도 시)</b>", text_auto='.1f',
                    color_discrete_sequence=['#27AE60', '#2980B9']
                )
                fig_type_defend.update_yaxes(range=[0, 100])
                st.plotly_chart(fig_type_defend, use_container_width=True)
            else:
                st.warning("분석할 유효한 Type 데이터가 존재하지 않습니다.")

        # --- TAB 4: 원본 데이터 ---
        with tab4:
            st.subheader("📋 누적 및 필터링된 통합 로우 데이터 (결함 보정 완료)")
            st.dataframe(filtered_df, use_container_width=True)

else:
    st.info("💡 오른쪽 사이드바 메뉴에서 분석 대상 경기 데이터 파일(Excel / CSV)을 먼저 업로드해 주세요.")