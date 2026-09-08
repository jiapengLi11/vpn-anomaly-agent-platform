async page => {
  // Offline regression: no model requests.
  await page.reload();
  await page.setViewportSize({width:1440,height:1000});
  await page.getByRole('button',{name:'清除本机记录',exact:true}).click();
  const fresh=page.getByRole('button',{name:'新对话',exact:true});
  if(await fresh.isEnabled()) await fresh.click();
  async function ask(question,index) {
    await page.getByRole('textbox',{name:index?'继续提问':'输入你的问题',exact:true}).fill(question);
    await page.getByRole('button',{name:index?'发送追问':'提问',exact:true}).click();
    await page.locator('.qa-turn').nth(index).locator('.answer-notice').waitFor();
  }
  await ask('开放集拒识',0);
  await ask('为什么呢',1);
  await ask('举个例子',2);
  const third=page.locator('.qa-turn').nth(2);
  await third.getByText('追问理解与检索词',{exact:true}).click();
  await third.getByText('开放集拒识 举个例子',{exact:true}).waitFor();
  await ask('UDP',3);
  const fourth=page.locator('.qa-turn').nth(3);
  await fourth.getByText('追问理解与检索词',{exact:true}).click();
  await fourth.getByText('按本次独立问题检索',{exact:true}).waitFor();
  await page.getByRole('button',{name:'新对话',exact:true}).click();
  await ask('举个例子',0);
  await page.getByText('请先说明你想继续了解的主题，例如：开放集拒识有什么局限？',{exact:true}).waitFor();
  return {chainedFollowup:'passed',topicSwitch:'passed',missingContext:'passed'};
}
