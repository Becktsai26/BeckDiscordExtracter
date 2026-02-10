// MutationObserver Injector Script
// Injected into Discord page via Playwright page.evaluate()
// Monitors chat DOM changes and extracts new messages as JSON via console.log

(function () {
    "use strict";

    // Guard: prevent double-injection
    if (window.__discordObserverInjected) {
        return;
    }
    window.__discordObserverInjected = true;

    // ── Helper: Extract author from an article node ──────────────────────
    // Discord article elements typically carry an aria-label like
    // "Username said …" or contain a header element with the author name.
    function extractAuthor(articleNode) {
        // Strategy 1: aria-label on the article itself (e.g. "TraderJoe said ...")
        var ariaLabel = articleNode.getAttribute("aria-label");
        if (ariaLabel) {
            // Common pattern: "<Author> said ..." or "<Author> 說了 ..."
            // We take everything before the first known separator.
            var separators = [" said", " 說了", " — "];
            for (var i = 0; i < separators.length; i++) {
                var idx = ariaLabel.indexOf(separators[i]);
                if (idx > 0) {
                    return ariaLabel.substring(0, idx).trim();
                }
            }
            // If no separator matched, return the full aria-label as fallback
            return ariaLabel.trim();
        }

        // Strategy 2: look for a header element inside the article
        var headerEl = articleNode.querySelector("h2, h3, [class*='header']");
        if (headerEl) {
            // Inside the header, look for a span that likely holds the username
            var spans = headerEl.querySelectorAll("span");
            for (var j = 0; j < spans.length; j++) {
                var text = (spans[j].textContent || "").trim();
                if (text.length > 0) {
                    return text;
                }
            }
            var headerText = (headerEl.textContent || "").trim();
            if (headerText.length > 0) {
                return headerText;
            }
        }

        // Strategy 3: look for an element with id containing "message-username"
        var usernameEl = articleNode.querySelector("[id*='message-username']");
        if (usernameEl) {
            var uText = (usernameEl.textContent || "").trim();
            if (uText.length > 0) {
                return uText;
            }
        }

        return "";
    }

    // ── Helper: Extract message content from an article node ─────────────
    function extractContent(articleNode) {
        // Strategy 1: look for an element with id containing "message-content"
        var contentEl = articleNode.querySelector("[id*='message-content']");
        if (contentEl) {
            var text = (contentEl.textContent || "").trim();
            if (text.length > 0) {
                return text;
            }
        }

        // Strategy 2: look for a div with role or data attribute hinting at content
        var divs = articleNode.querySelectorAll("div");
        for (var i = 0; i < divs.length; i++) {
            var div = divs[i];
            var id = div.getAttribute("id") || "";
            if (id.indexOf("message-content") !== -1) {
                var t = (div.textContent || "").trim();
                if (t.length > 0) {
                    return t;
                }
            }
        }

        // Strategy 3: fallback – grab all text from the article, excluding
        // header and time elements to avoid mixing author/timestamp into content
        var clone = articleNode.cloneNode(true);
        var headersToRemove = clone.querySelectorAll("h2, h3, time, [id*='message-username']");
        for (var j = 0; j < headersToRemove.length; j++) {
            headersToRemove[j].remove();
        }
        var fallback = (clone.textContent || "").trim();
        return fallback;
    }

    // ── Helper: Extract timestamp from an article node ───────────────────
    function extractTimestamp(articleNode) {
        // Look for <time> elements with a datetime attribute (stable, semantic)
        var timeEl = articleNode.querySelector("time[datetime]");
        if (timeEl) {
            return timeEl.getAttribute("datetime");
        }

        // Fallback: look for any <time> element
        var anyTime = articleNode.querySelector("time");
        if (anyTime) {
            return (anyTime.textContent || "").trim();
        }

        // Last resort: return current ISO timestamp
        return new Date().toISOString();
    }

    // ── Helper: Extract channel name from the page ───────────────────────
    function extractChannel() {
        // Strategy 1: look for an h1 element that typically holds the channel name
        var h1Elements = document.querySelectorAll("h1");
        for (var i = 0; i < h1Elements.length; i++) {
            var text = (h1Elements[i].textContent || "").trim();
            if (text.length > 0) {
                return text;
            }
        }

        // Strategy 2: look for elements with specific roles/attributes for channel name
        var headingEls = document.querySelectorAll("[role='heading']");
        for (var j = 0; j < headingEls.length; j++) {
            var hText = (headingEls[j].textContent || "").trim();
            if (hText.length > 0) {
                return hText;
            }
        }

        // Strategy 3: extract from document title
        // Discord titles are typically formatted as "#channel-name | Server Name - Discord"
        var title = document.title || "";
        if (title.length > 0) {
            // Try to extract channel name from title pattern
            var hashMatch = title.match(/^#?([\w-]+)/);
            if (hashMatch) {
                return hashMatch[1];
            }
            // Return the part before the first separator
            var pipeIdx = title.indexOf("|");
            if (pipeIdx > 0) {
                return title.substring(0, pipeIdx).replace(/^#/, "").trim();
            }
            var dashIdx = title.indexOf(" - ");
            if (dashIdx > 0) {
                return title.substring(0, dashIdx).replace(/^#/, "").trim();
            }
            return title.trim();
        }

        return "";
    }

    // ── Core: Extract data from an article node and log as JSON ──────────
    function extractAndLog(articleNode) {
        try {
            var author = extractAuthor(articleNode);
            var content = extractContent(articleNode);
            var timestamp = extractTimestamp(articleNode);
            var channel = extractChannel();

            // Silently skip nodes that don't contain expected message structure
            // (Requirement 10.4: skip nodes without expected structure)
            if (!author && !content) {
                return;
            }

            var data = {
                type: "DISCORD_MESSAGE",
                author: author,
                content: content,
                timestamp: timestamp,
                channel: channel
            };

            console.log(JSON.stringify(data));
        } catch (e) {
            // Silently skip any extraction errors (Requirement 10.4)
        }
    }

    // ── Core: Inject the MutationObserver ────────────────────────────────
    function injectObserver() {
        // 1. Find chat list container using semantic selectors
        //    (Requirement 4.6: use stable DOM attributes, not hashed class names)
        var chatContainer =
            document.querySelector('[role="list"][data-list-id="chat-messages"]') ||
            document.querySelector('ol[data-list-id="chat-messages"]') ||
            document.querySelector('[data-list-id="chat-messages"]');

        if (!chatContainer) {
            // Container not found yet – retry after a short delay
            setTimeout(injectObserver, 2000);
            return;
        }

        // 2. Ensure scroll position is at the bottom
        //    (Requirement 4.7: lock scroll to bottom for virtual scrolling)
        var scrollContainer = chatContainer.closest('[class*="scroller"]') || chatContainer;
        scrollContainer.scrollTop = scrollContainer.scrollHeight;

        // 3. Create MutationObserver watching childList + subtree
        //    (Requirement 4.2: monitor childList and subtree changes)
        var observer = new MutationObserver(function (mutations) {
            for (var m = 0; m < mutations.length; m++) {
                var addedNodes = mutations[m].addedNodes;
                for (var n = 0; n < addedNodes.length; n++) {
                    var node = addedNodes[n];

                    // Only process element nodes
                    if (node.nodeType !== Node.ELEMENT_NODE) {
                        continue;
                    }

                    // 4. For each added node, find [role="article"] elements
                    //    (Requirement 4.6: use role="article" to locate messages)

                    // Check if the node itself is an article
                    if (node.matches && node.matches('[role="article"]')) {
                        extractAndLog(node);
                    }

                    // Check for article descendants
                    if (node.querySelectorAll) {
                        var articles = node.querySelectorAll('[role="article"]');
                        for (var a = 0; a < articles.length; a++) {
                            extractAndLog(articles[a]);
                        }
                    }
                }
            }
        });

        // 5. Start observing
        observer.observe(chatContainer, {
            childList: true,
            subtree: true
        });

        // 6. Periodic scroll check (every 5 seconds, low frequency)
        //    (Requirement 4.8: auto-scroll back to bottom if drifted)
        //    (Requirement 11.4: no high-frequency DOM access, ≤ 1/sec)
        setInterval(function () {
            var scroller =
                chatContainer.closest('[class*="scroller"]') ||
                chatContainer;
            if (scroller) {
                var isAtBottom =
                    scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 50;
                if (!isAtBottom) {
                    scroller.scrollTop = scroller.scrollHeight;
                }
            }
        }, 5000);
    }

    // ── Entry point ──────────────────────────────────────────────────────
    injectObserver();
})();
