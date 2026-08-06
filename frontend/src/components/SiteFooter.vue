<script setup>
/* 전역 푸터 — 모든 화면의 문서 맨 아래.
 * 내용은 이 프로젝트가 무엇인지 — 해커톤 산출물임을 밝히는 게 먼저다. */
import { RouterLink } from 'vue-router'
import logoMark from '../assets/logo-mark.png'

const YEAR = 2026
</script>

<template>
  <footer class="ft">
    <div class="ft-in">
      <div class="col about">
        <img :src="logoMark" alt="MJC Club Archive" width="128" height="59">
        <p>
          명지전문대학 동아리를 <b>소개글이 아니라 활동 기록</b>으로 보는 아카이브입니다.
          동아리장이 사진과 메모만 올리면 명지전문대학 AI가 활동 글 초안을 만듭니다.
        </p>
      </div>

      <nav class="col" aria-label="둘러보기">
        <h2>둘러보기</h2>
        <RouterLink to="/">홈</RouterLink>
        <RouterLink to="/archive">동아리 아카이브</RouterLink>
        <RouterLink to="/clubs/new">동아리 개설 신청</RouterLink>
        <RouterLink to="/me">내 정보</RouterLink>
        <RouterLink to="/terms">이용약관 · 개인정보 처리방침</RouterLink>
      </nav>

      <div class="col">
        <h2>만든 사람</h2>
        <p class="team">박찬우 · 이우진 · 김태희</p>
        <p class="sub">2026 명지전문대 RISE사업단 AI 해커톤 경진대회 출품작 (주제 2)</p>
      </div>
    </div>

    <p class="ft-bottom">
      <span class="latin">&copy; {{ YEAR }} MJC Club Archive</span>
      <span class="dot">·</span>
      <span>학내 구성원용 시연 서비스입니다. 실제 학사 정보와 다를 수 있습니다.</span>
    </p>
  </footer>
</template>

<style scoped>
.ft {
  border-top: 1px solid var(--line);
  background: var(--bg);
  margin-top: 40px;
  /* 메인은 스냅 스크롤이다. 정지점을 하나 더 두지 않으면 mandatory 스냅이
     브랜드 화면으로 되돌려 푸터에 닿을 수 없다 */
  scroll-snap-align: end;
}

.ft-in {
  width: min(1180px, calc(100vw - 40px));
  margin: 0 auto;
  padding: clamp(34px, 5vh, 54px) 0 26px;
  display: grid;
  grid-template-columns: minmax(260px, 1.6fr) 1fr 1fr;
  gap: clamp(24px, 4vw, 60px);
  align-items: start;
}

.col h2 {
  margin: 0 0 12px;
  font-size: 11px; font-weight: 700; letter-spacing: .13em;
  color: var(--dim); text-transform: uppercase;
}
.col a { display: block; font-size: 13.5px; padding: 4px 0; color: var(--dim); }
.col a:hover { color: var(--accent); }

.about img { width: 116px; height: auto; display: block; margin-bottom: 12px; }
.about p { margin: 0; font-size: 13px; line-height: 1.85; color: var(--dim); max-width: 46ch; }
.about b { color: var(--ink); }

.team { margin: 0 0 6px; font-size: 13.5px; font-weight: 700; }
.col .sub { margin: 0; line-height: 1.7; }

.ft-bottom {
  width: min(1180px, calc(100vw - 40px));
  margin: 0 auto;
  padding: 16px 0 26px;
  border-top: 1px solid var(--line);
  display: flex; flex-wrap: wrap; gap: 8px;
  font-size: 12px; color: var(--dim);
}
.ft-bottom .dot { opacity: .6; }

@media (max-width: 860px) {
  .ft-in { grid-template-columns: 1fr; gap: 26px; }
}
</style>
