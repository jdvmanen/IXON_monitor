const ixonUrlPattern = "https://portal.ixon.cloud/*";
const ixonPortalUrl = "https://portal.ixon.cloud/portal/devices";

async function activateIxonPortal() {
  const [existingTab] = await chrome.tabs.query({ url: [ixonUrlPattern] });

  if (existingTab?.id !== undefined) {
    await chrome.tabs.update(existingTab.id, { active: true });
    await chrome.windows.update(existingTab.windowId, { focused: true });
  } else {
    await chrome.tabs.create({ url: ixonPortalUrl });
  }

  window.close();
}

activateIxonPortal().catch(async () => {
  await chrome.tabs.create({ url: ixonPortalUrl });
  window.close();
});
