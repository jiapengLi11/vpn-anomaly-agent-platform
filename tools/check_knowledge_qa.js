async page => {
  await page.setViewportSize({width:1440,height:1000});
  await page.getByText('知识检索开发集',{exact:true}).waitFor();
  await page.getByText('91.7%',{exact:true}).waitFor();
  await page.getByText('自编开发集，仅用于防回归，不代表真实业务准确率。',{exact:true}).waitFor();
  await page.getByRole('button', {name:'模型原理 开放集拒识是什么意思？'}).click();
  await page.getByRole('button', {name:'提问',exact:true}).click();
  await page.getByRole('button', {name:'[1] 查看来源',exact:true}).waitFor();
  await page.getByRole('button', {name:'[1] 查看来源',exact:true}).click();
  if (await page.locator('.qa-source.highlighted').count() !== 1) throw new Error('Citation not selected');
  await page.getByText('版本和引用标识', {exact:true}).click();
  await page.evaluate(() => window.scrollTo(0,0));
  await page.screenshot({path:'docs/assets/knowledge-qa.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.evaluate(() => window.scrollTo(0,0));
  if(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Mobile overflow');
  await page.screenshot({path:'docs/assets/knowledge-qa-mobile.png',fullPage:true,animations:'disabled'});
  await page.getByRole('textbox',{name:'继续提问',exact:true}).fill('为什么呢');
  await page.getByRole('button',{name:'发送追问',exact:true}).click();
  await page.waitForFunction(() => document.querySelectorAll('.qa-turn').length === 2 && document.querySelectorAll('.answer-paragraph').length === 2);
  await page.getByRole('button',{name:'新对话',exact:true}).click();
  await page.getByRole('heading',{name:'你想了解什么？',exact:true}).waitFor();
  if(await page.locator('.qa-source').count()) throw new Error('Reset kept old sources');
  await page.getByRole('textbox',{name:'输入你的问题',exact:true}).fill('xyzunmatched987');
  await page.getByRole('button',{name:'提问',exact:true}).click();
  await page.getByText('知识库未找到相关资料，请补充具体术语或换个问法。',{exact:true}).waitFor();
  await page.getByRole('button',{name:'新对话',exact:true}).click();
  await page.route('http://127.0.0.1:8090/api/knowledge/answer/stream', route => route.fulfill({
    status:200,contentType:'text/event-stream',body:'event: done\ndata: '+JSON.stringify({status:'SKIPPED',provider:'deepseek',sources:[],paragraphs:[],message:'请在本地后端配置 DS_API_KEY（也兼容 DEEPSEEK_API_KEY）。'})+'\n\n'
  }));
  await page.getByRole('checkbox',{name:'使用本地 DeepSeek'}).check();
  await page.getByRole('textbox',{name:'输入你的问题',exact:true}).fill('开放集拒识');
  await page.getByRole('button',{name:'提问',exact:true}).click();
  await page.getByText('请在本地后端配置 DS_API_KEY（也兼容 DEEPSEEK_API_KEY）。',{exact:true}).waitFor();
  await page.unroute('http://127.0.0.1:8090/api/knowledge/answer/stream');
}
