async page => {
  // Mock browser transport only: exercises draft withdrawal and stop without a paid API request.
  await page.reload();
  await page.getByRole('button',{name:'清除本机记录',exact:true}).click();
  const fresh=page.getByRole('button',{name:'新对话',exact:true});
  if(await fresh.isEnabled()) await fresh.click();
  await page.getByRole('checkbox',{name:'在本机保留会话 7 天'}).check();
  await page.getByRole('checkbox',{name:'使用本地 DeepSeek'}).check();
  await page.evaluate(()=>{
    window.originalFetch=window.fetch;
    window.fetch=async(url,options)=>{
      if(!String(url).endsWith('/api/knowledge/answer/stream')) return window.originalFetch(url,options);
      const encoder=new TextEncoder();
      return new Response(new ReadableStream({start(controller){
        controller.enqueue(encoder.encode('event: draft\ndata: {"text":"未校验测试草稿"}\n\n'));
        options.signal.addEventListener('abort',()=>{window.streamAbortObserved=true;controller.error(new DOMException('Aborted','AbortError'));});
      }}),{headers:{'Content-Type':'text/event-stream'}});
    };
  });
  await page.getByRole('textbox',{name:'输入你的问题',exact:true}).fill('开放集拒识');
  await page.getByRole('button',{name:'提问',exact:true}).click();
  await page.locator('.stream-draft').waitFor();
  await page.getByRole('button',{name:'停止生成',exact:true}).click();
  await page.getByText('已停止生成，未完成草稿不会写入记忆。',{exact:true}).waitFor();
  if(await page.locator('.stream-draft').count()) throw new Error('Cancelled draft not withdrawn');
  if(!await page.evaluate(()=>window.streamAbortObserved)) throw new Error('Abort signal not propagated');
  if(await page.evaluate(()=>JSON.parse(localStorage.getItem('vpn-knowledge-conversations-v1')).sessions.some(s=>s.turns.length))) throw new Error('Cancelled answer stored');
  await page.reload();
  if(await page.locator('.qa-turn').count()) throw new Error('Cancelled answer restored');
  await page.getByRole('button',{name:'清除本机记录',exact:true}).click();
  await page.getByRole('checkbox',{name:'在本机保留会话 7 天'}).check();
  await page.getByRole('textbox',{name:'输入你的问题',exact:true}).fill('开放集拒识');
  await page.getByRole('button',{name:'提问',exact:true}).click();
  await page.locator('.answer-paragraph').first().waitFor();
  await page.reload();
  await page.locator('.answer-paragraph').first().waitFor();
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'docs/assets/knowledge-qa-memory-mobile.png',fullPage:true,animations:'disabled'});
  await page.getByRole('button',{name:'清除本机记录',exact:true}).click();
  await page.reload();
  return {stop:'passed',draftWithdrawal:'passed',memoryExclusion:'passed'};
}
