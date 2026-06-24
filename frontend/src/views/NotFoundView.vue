<template>
  <main class="not-found">
    <ElResult icon="warning" title="页面不存在" sub-title="这个知识节点还没被 TechBrain 收录。">
      <template #extra>
        <ElButton type="primary" tag="router-link" to="/">返回首页</ElButton>
      </template>
    </ElResult>
  </main>
</template>
