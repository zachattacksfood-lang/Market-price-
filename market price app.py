<!DOCTYPE html>
<html lang="en">
<head>
   <meta charset="UTF-8">
   <meta name="viewport" content="width=device-width, initial-scale=1.0">
   <title>Stock & Crypto Tracker</title>
   <script src="https://cdn.tailwindcss.com"></script>
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
   <script type="module">
       import { initializeApp } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js";
       import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut, onAuthStateChanged, signInWithCustomToken } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js";
       import { getFirestore, doc, setDoc, deleteDoc, onSnapshot, collection, addDoc, serverTimestamp, setLogLevel } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-firestore.js";
       
       setLogLevel('debug');
       
       let db, auth;
       let currentUser = null;
       let unsubscribePortfolio = null;
       let unsubscribeWatchlist = null;
       const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';
       const firebaseConfig = JSON.parse(typeof __firebase_config !== 'undefined' ? __firebase_config : '{}');

       // Global state
       window.portfolioItems = {};
       window.watchlistItems = [];

       // Check for required Firebase variables before initialization
       if (Object.keys(firebaseConfig).length > 0) {
           const app = initializeApp(firebaseConfig);
           auth = getAuth(app);
           db = getFirestore(app);

           // Authentication state listener
           onAuthStateChanged(auth, async (user) => {
               currentUser = user;
               updateUIForAuthState();
               if (user) {
                   initializeListeners();
               } else {
                   // Unsubscribe from previous listeners when user logs out
                   if (unsubscribePortfolio) unsubscribePortfolio();
                   if (unsubscribeWatchlist) unsubscribeWatchlist();
               }
           });
           
       } else {
           console.error("Firebase config is missing. The application will not be able to save data.");
       }

       const initializeListeners = () => {
           // Set up realtime listeners for portfolio and watchlist
           if (currentUser && currentUser.uid) {
               const userId = currentUser.uid;
               unsubscribePortfolio = onSnapshot(collection(db, `artifacts//users//portfolio`), (snapshot) => {
                   const portfolioData = {};
                   snapshot.forEach(doc => {
                       portfolioData[doc.id] = doc.data();
                   });
                   window.portfolioItems = portfolioData;
                   renderPortfolio();
               });

               unsubscribeWatchlist = onSnapshot(collection(db, `artifacts//users//watchlist`), (snapshot) => {
                   const watchlistItems = [];
                   snapshot.forEach(doc => {
                       // Correctly add the document ID to the data object
                       watchlistItems.push({ id: doc.id, ...doc.data() });
                   });
                   window.watchlistItems = watchlistItems;
                   renderWatchlist();
               });
           }
       };
       
       const updateUIForAuthState = () => {
           const loggedInInfo = document.getElementById('logged-in-info');
           const portfolioTabLink = document.querySelector('[data-tab="portfolio"]');
           const watchlistTabLink = document.querySelector('[data-tab="watchlist"]');
           const loginTabLink = document.querySelector('[data-tab="login"]');
           const signupTabLink = document.querySelector('[data-tab="signup"]');
           
           if (currentUser) {
               loggedInInfo.classList.remove('hidden');
               document.getElementById('logged-in-email').textContent = currentUser.email;
               portfolioTabLink.classList.remove('hidden');
               watchlistTabLink.classList.remove('hidden');
               loginTabLink.classList.add('hidden');
               signupTabLink.classList.add('hidden');
           } else {
               loggedInInfo.classList.add('hidden');
               portfolioTabLink.classList.add('hidden');
               watchlistTabLink.classList.add('hidden');
               loginTabLink.classList.remove('hidden');
               signupTabLink.classList.remove('hidden');
           }
       };

       const renderPortfolio = async () => {
           const portfolioList = document.getElementById('portfolio-list');
           if (!portfolioList) return;
           portfolioList.innerHTML = '';
           let totalValue = 0;

           const updatePortfolioPromises = Object.entries(window.portfolioItems).map(async ([id, item]) => {
               const { price, error } = await window.fetchPrice(item.symbol, item.type);
               const currentPrice = price || item.purchasePrice;
               const currentValue = (currentPrice * item.quantity);
               totalValue += currentValue;
               
               const profitLoss = (currentValue - (item.purchasePrice * item.quantity));
               const profitLossClass = profitLoss >= 0 ? 'text-lime-500' : 'text-red-500';

               const li = document.createElement('li');
               li.className = 'bg-neutral-900 p-4 rounded-lg flex justify-between items-center mb-2';
               li.innerHTML = `
                   <div>
                       <p class="text-lg font-semibold text-lime-400"> <span class="text-sm font-normal text-neutral-400">()</span></p>
                       <p class="text-sm text-neutral-400">Shares: </p>
                       <p class="text-sm text-neutral-400">Current Value: <span class="text-lime-500">$</span></p>
                       <p class="text-sm text-neutral-400">P/L: <span class="">$</span></p>
                   </div>
                   <div class="flex space-x-2">
                       <button class="delete-portfolio-btn p-2 rounded-full bg-red-600 hover:bg-red-700 text-white transition-colors duration-200" data-id="">
                           <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                               <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                           </svg>
                       </button>
                   </div>
               `;
               portfolioList.appendChild(li);
           });
           await Promise.all(updatePortfolioPromises);
           document.getElementById('total-portfolio-value').textContent = `$`;
       };

       const renderWatchlist = () => {
           const watchlistList = document.getElementById('watchlist-list');
           if (!watchlistList) return;
           watchlistList.innerHTML = '';
           window.watchlistItems.forEach(item => {
               const li = document.createElement('li');
               li.className = 'bg-neutral-900 p-3 rounded-lg flex justify-between items-center mb-2';
               li.innerHTML = `
                   <p class="text-lg font-semibold text-lime-400"> <span class="text-sm font-normal text-neutral-400">()</span></p>
                   <button class="delete-watchlist-btn p-2 rounded-full bg-red-600 hover:bg-red-700 text-white transition-colors duration-200" data-id="">
                       <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                           <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                       </svg>
                   </button>
               `;
               watchlistList.appendChild(li);
           });
       };

       document.addEventListener('DOMContentLoaded', () => {
           // Main elements
           const stockForm = document.getElementById('stock-form');
           const cryptoForm = document.getElementById('crypto-form');
           const tabLinks = document.querySelectorAll('.tab-link');
           const loginLink = document.querySelector('[data-tab="login"]');
           const signupLink = document.querySelector('[data-tab="signup"]');
           
           // Menu elements
           const menuButton = document.getElementById('menu-button');
           const menuPanel = document.getElementById('menu-panel');

           // Account elements
           const signUpForm = document.getElementById('signup-form');
           const loginForm = document.getElementById('login-form');
           const logoutButton = document.getElementById('logout-button');

           // Portfolio & Watchlist elements
           const portfolioForm = document.getElementById('add-portfolio-item');
           const watchlistForm = document.getElementById('add-watchlist-item');

           // Recommendations elements
           const getRecommendationsBtn = document.getElementById('get-recommendations-btn');
           const recommendationsOutput = document.getElementById('recommendations-output');
           const recommendationsSymbolInput = document.getElementById('recommendations-symbol');

           // API Key
           const API_KEY = '8PUN5WHTBIULJM0L';

           // Function to show a message
           const showMessage = (messageBox, messageText, text, type = 'error') => {
               messageText.textContent = text;
               messageBox.classList.remove('hidden', 'bg-red-900', 'text-red-400', 'bg-lime-900', 'text-lime-300');
               if (type === 'error') {
                   messageBox.classList.add('bg-red-900', 'text-red-400');
               } else if (type === 'success') {
                   messageBox.classList.add('bg-lime-900', 'text-lime-300');
               }
           };

           // Function to clear a message
           const clearMessage = (messageBox, messageText) => {
               messageBox.classList.add('hidden');
               messageText.textContent = '';
           };

           // Function to set loading state
           const setLoadingState = (btn, isLoading, text) => {
               btn.disabled = isLoading;
               if (isLoading) {
                   btn.textContent = 'Loading...';
                   btn.classList.add('bg-neutral-800', 'cursor-not-allowed', 'text-neutral-500');
                   btn.classList.remove('bg-lime-500', 'hover:bg-lime-600', 'text-black');
               } else {
                   btn.textContent = text;
                   btn.classList.remove('bg-neutral-800', 'cursor-not-allowed', 'text-neutral-500');
                   btn.classList.add('bg-lime-500', 'hover:bg-lime-600', 'text-black');
               }
           };
           
           // Function to fetch price based on type (stock or crypto) and timeframe
           const fetchPrice = async (symbol, type, timeframe = 'realtime') => {
               let url = '';
               let priceKey;
               let dataKey;

               if (type === 'stock') {
                   switch(timeframe) {
                       case 'realtime':
                           url = `https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=&apikey=`;
                           dataKey = 'Global Quote';
                           priceKey = '05. price';
                           break;
                       case '1min':
                       case '5min':
                       case '15min':
                           url = `https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=&interval=&apikey=`;
                           dataKey = `Time Series ()`;
                           priceKey = '4. close';
                           break;
                       case 'daily':
                           url = `https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=&apikey=`;
                           dataKey = 'Time Series (Daily)';
                           priceKey = '4. close';
                           break;
                       case 'weekly':
                           url = `https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol=&apikey=`;
                           dataKey = 'Time Series (Weekly)';
                           priceKey = '4. close';
                           break;
                       case 'monthly':
                           url = `https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY&symbol=&apikey=`;
                           dataKey = 'Time Series (Monthly)';
                           priceKey = '4. close';
                           break;
                   }
               } else if (type === 'crypto') {
                   switch(timeframe) {
                       case 'daily':
                           url = `https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol=&market=USD&apikey=`;
                           dataKey = 'Time Series (Digital Currency Daily)';
                           priceKey = '4b. close (USD)';
                           break;
                       case 'weekly':
                           url = `https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_WEEKLY&symbol=&market=USD&apikey=`;
                           dataKey = 'Time Series (Digital Currency Weekly)';
                           priceKey = '4b. close (USD)';
                           break;
                       case 'monthly':
                           url = `https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_MONTHLY&symbol=&market=USD&apikey=`;
                           dataKey = 'Time Series (Digital Currency Monthly)';
                           priceKey = '4b. close (USD)';
                           break;
                   }
               }

               try {
                   const response = await fetch(url);
                   const data = await response.json();
                   
                   if (data['Error Message'] || data['Note']) {
                       return { price: null, error: 'Invalid symbol or API limit reached.' };
                   }
                   
                   let price = null;
                   if (dataKey) {
                       const timeSeriesData = data[dataKey];
                       if (timeSeriesData) {
                           const latestDate = Object.keys(timeSeriesData)[0];
                           price = parseFloat(timeSeriesData[latestDate][priceKey]);
                       }
                   }

                   if (price) {
                       return { price, error: null };
                   } else {
                       return { price: null, error: 'Could not fetch data. The symbol might be invalid or there is no recent data.' };
                   }
               } catch (error) {
                   console.error('Error fetching data:', error);
                   return { price: null, error: 'Failed to fetch data. Please check your internet connection.' };
               }
           };
           window.fetchPrice = fetchPrice;

           // Stock form submission handler
           stockForm.addEventListener('submit', async (event) => {
               event.preventDefault();
               const stockSymbolInput = document.getElementById('stock-symbol');
               const stockTimeframeInput = document.getElementById('stock-timeframe');
               const stockVolatilityInput = document.getElementById('stock-volatility');
               const stockPriceInput = document.getElementById('stock-price');
               const resultsSection = document.getElementById('stock-results-section');
               const stockStopLossResult = document.getElementById('stock-stop-loss-result');
               const stockSellPointResult = document.getElementById('stock-sell-point-result');
               const messageBox = document.getElementById('stock-message-box');
               const messageText = document.getElementById('stock-message-text');
               const calculateBtn = document.getElementById('stock-calculate-btn');

               clearMessage(messageBox, messageText);
               setLoadingState(calculateBtn, true, 'Calculate');

               const symbol = stockSymbolInput.value.toUpperCase();
               const timeframe = stockTimeframeInput.value;
               const volatility = parseFloat(stockVolatilityInput.value);

               if (!symbol || isNaN(volatility) || volatility <= 0) {
                   showMessage(messageBox, messageText, 'Please enter a valid symbol and volatility percentage.');
                   setLoadingState(calculateBtn, false, 'Calculate');
                   return;
               }

               const { price, error } = await fetchPrice(symbol, 'stock', timeframe);
               
               if (price) {
                   stockPriceInput.value = price.toFixed(2);
                   const stopLoss = price * (1 - volatility / 100);
                   const sellPoint = price * (1 + volatility / 100);
                   stockStopLossResult.textContent = `$`;
                   stockSellPointResult.textContent = `$`;
                   resultsSection.classList.remove('hidden');
                   showMessage(messageBox, messageText, 'Calculation complete!', 'success');
               } else {
                   resultsSection.classList.add('hidden');
                   showMessage(messageBox, messageText, error);
               }
               
               setLoadingState(calculateBtn, false, 'Calculate');
           });

           // Crypto form submission handler
           cryptoForm.addEventListener('submit', async (event) => {
               event.preventDefault();
               const cryptoSymbolInput = document.getElementById('crypto-symbol');
               const cryptoTimeframeInput = document.getElementById('crypto-timeframe');
               const cryptoVolatilityInput = document.getElementById('crypto-volatility');
               const cryptoPriceInput = document.getElementById('crypto-price');
               const resultsSection = document.getElementById('crypto-results-section');
               const cryptoStopLossResult = document.getElementById('crypto-stop-loss-result');
               const cryptoSellPointResult = document.getElementById('crypto-sell-point-result');
               const messageBox = document.getElementById('crypto-message-box');
               const messageText = document.getElementById('crypto-message-text');
               const calculateBtn = document.getElementById('crypto-calculate-btn');

               clearMessage(messageBox, messageText);
               setLoadingState(calculateBtn, true, 'Calculate');

               const symbol = cryptoSymbolInput.value.toUpperCase();
               const timeframe = cryptoTimeframeInput.value;
               const volatility = parseFloat(cryptoVolatilityInput.value);

               if (!symbol || isNaN(volatility) || volatility <= 0) {
                   showMessage(messageBox, messageText, 'Please enter a valid symbol and volatility percentage.');
                   setLoadingState(calculateBtn, false, 'Calculate');
                   return;
               }

               const { price, error } = await fetchPrice(symbol, 'crypto', timeframe);

               if (price) {
                   cryptoPriceInput.value = price.toFixed(2);
                   const stopLoss = price * (1 - volatility / 100);
                   const sellPoint = price * (1 + volatility / 100);
                   cryptoStopLossResult.textContent = `$`;
                   cryptoSellPointResult.textContent = `$`;
                   resultsSection.classList.remove('hidden');
                   showMessage(messageBox, messageText, 'Calculation complete!', 'success');
               } else {
                   resultsSection.classList.add('hidden');
                   showMessage(messageBox, messageText, error);
               }
               
               setLoadingState(calculateBtn, false, 'Calculate');
           });

           // Recommendations button handler
           getRecommendationsBtn.addEventListener('click', async () => {
               const messageBox = document.getElementById('recommendations-message-box');
               const messageText = document.getElementById('recommendations-message-text');
               const recommendationsOutput = document.getElementById('recommendations-output');
               const symbol = recommendationsSymbolInput.value.toUpperCase();
               
               if (!symbol) {
                   showMessage(messageBox, messageText, 'Please enter a stock or crypto symbol.');
                   return;
               }

               clearMessage(messageBox, messageText);
               setLoadingState(getRecommendationsBtn, true, 'Getting Insights...');
               recommendationsOutput.innerHTML = '';

               // Call to the Gemini API to get a summary
               const userQuery = `Provide a concise, single-paragraph summary of recent news for the stock or crypto market for .`;
               const apiKey = "";
               const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key=`;

               try {
                   const payload = {
                       contents: [{ parts: [{ text: userQuery }] }],
                   };
                   const response = await fetch(apiUrl, {
                       method: 'POST',
                       headers: { 'Content-Type': 'application/json' },
                       body: JSON.stringify(payload)
                   });
                   const result = await response.json();
                   
                   const candidate = result.candidates?.[0];
                   if (candidate && candidate.content?.parts?.[0]?.text) {
                       const summaryText = candidate.content.parts[0].text;
                       recommendationsOutput.innerHTML = `<p></p>`;
                       showMessage(messageBox, messageText, 'Insights updated!', 'success');
                   } else {
                       showMessage(messageBox, messageText, 'No insights found. The symbol may be invalid.');
                   }
               } catch (error) {
                   console.error('Error fetching data:', error);
                   showMessage(messageBox, messageText, 'Failed to fetch insights. Please try again.');
               }
               
               setLoadingState(getRecommendationsBtn, false, 'Get Insights');
           });

           // Sign Up form submission handler
           signUpForm.addEventListener('submit', async (e) => {
               e.preventDefault();
               const email = document.getElementById('signup-email').value;
               const password = document.getElementById('signup-password').value;
               const messageBox = document.getElementById('account-message-box');
               const messageText = document.getElementById('account-message-text');

               clearMessage(messageBox, messageText);

               try {
                   await createUserWithEmailAndPassword(auth, email, password);
                   showMessage(messageBox, messageText, 'Account created successfully! You are now logged in.', 'success');
               } catch (error) {
                   showMessage(messageBox, messageText, `Error creating account: `);
               }
           });

           // Login form submission handler
           loginForm.addEventListener('submit', async (e) => {
               e.preventDefault();
               const email = document.getElementById('login-email').value;
               const password = document.getElementById('login-password').value;
               const messageBox = document.getElementById('account-message-box');
               const messageText = document.getElementById('account-message-text');

               clearMessage(messageBox, messageText);
               
               try {
                   await signInWithEmailAndPassword(auth, email, password);
                   showMessage(messageBox, messageText, 'Logged in successfully!', 'success');
               } catch (error) {
                   showMessage(messageBox, messageText, `Error logging in: `);
               }
           });

           // Logout button handler
           logoutButton.addEventListener('click', async () => {
               await signOut(auth);
               const messageBox = document.getElementById('account-message-box');
               const messageText = document.getElementById('account-message-text');
               showMessage(messageBox, messageText, 'Logged out successfully.', 'success');
           });

           // Portfolio form submission handler
           portfolioForm.addEventListener('submit', async (event) => {
               event.preventDefault();
               const symbolInput = document.getElementById('portfolio-symbol');
               const typeInput = document.getElementById('portfolio-type');
               const quantityInput = document.getElementById('portfolio-quantity');
               const priceInput = document.getElementById('portfolio-price');
               const addBtn = document.getElementById('add-portfolio-btn');
               const messageBox = document.getElementById('portfolio-message-box');
               const messageText = document.getElementById('portfolio-message-text');
               
               clearMessage(messageBox, messageText);
               setLoadingState(addBtn, true, 'Add to Portfolio');

               if (!currentUser) {
                   showMessage(messageBox, messageText, 'Please log in to add items to your portfolio.');
                   setLoadingState(addBtn, false, 'Add to Portfolio');
                   return;
               }

               const symbol = symbolInput.value.toUpperCase();
               const type = typeInput.value;
               const quantity = parseFloat(quantityInput.value);
               const purchasePrice = parseFloat(priceInput.value);

               if (!symbol || !type || isNaN(quantity) || quantity <= 0 || isNaN(purchasePrice) || purchasePrice <= 0) {
                   showMessage(messageBox, messageText, 'Please fill out all fields with valid data.');
                   setLoadingState(addBtn, false, 'Add to Portfolio');
                   return;
               }
               
               try {
                   await addDoc(collection(db, `artifacts//users//portfolio`), {
                       symbol,
                       type,
                       quantity,
                       purchasePrice,
                       timestamp: serverTimestamp()
                   });
                   showMessage(messageBox, messageText, 'Item added to portfolio!', 'success');
                   symbolInput.value = '';
                   quantityInput.value = '';
                   priceInput.value = '';
               } catch (e) {
                   console.error("Error adding document: ", e);
                   showMessage(messageBox, messageText, 'Error adding item to portfolio.');
               }
               setLoadingState(addBtn, false, 'Add to Portfolio');
           });

           // Watchlist form submission handler
           watchlistForm.addEventListener('submit', async (event) => {
               event.preventDefault();
               const symbolInput = document.getElementById('watchlist-symbol');
               const typeInput = document.getElementById('watchlist-type');
               const addBtn = document.getElementById('add-watchlist-btn');
               const messageBox = document.getElementById('watchlist-message-box');
               const messageText = document.getElementById('watchlist-message-text');

               clearMessage(messageBox, messageText);
               setLoadingState(addBtn, true, 'Add to Watchlist');

               if (!currentUser) {
                   showMessage(messageBox, messageText, 'Please log in to add items to your watchlist.');
                   setLoadingState(addBtn, false, 'Add to Watchlist');
                   return;
               }

               const symbol = symbolInput.value.toUpperCase();
               const type = typeInput.value;

               if (!symbol || !type) {
                   showMessage(messageBox, messageText, 'Please enter a valid symbol and select a type.');
                   setLoadingState(addBtn, false, 'Add to Watchlist');
                   return;
               }
               
               try {
                   await addDoc(collection(db, `artifacts//users//watchlist`), {
                       symbol,
                       type,
                       timestamp: serverTimestamp()
                   });
                   showMessage(messageBox, messageText, 'Item added to watchlist!', 'success');
                   symbolInput.value = '';
               } catch (e) {
                   console.error("Error adding document: ", e);
                   showMessage(messageBox, messageText, 'Error adding item to watchlist.');
               }
               setLoadingState(addBtn, false, 'Add to Watchlist');
           });

           // Delete portfolio item handler
           document.getElementById('portfolio-list').addEventListener('click', async (e) => {
               if (!currentUser) return;
               if (e.target.closest('.delete-portfolio-btn')) {
                   const id = e.target.closest('.delete-portfolio-btn').getAttribute('data-id');
                   const docRef = doc(db, `artifacts//users//portfolio`, id);
                   await deleteDoc(docRef);
               }
           });

           // Delete watchlist item handler
           document.getElementById('watchlist-list').addEventListener('click', async (e) => {
               if (!currentUser) return;
               if (e.target.closest('.delete-watchlist-btn')) {
                   const id = e.target.closest('.delete-watchlist-btn').getAttribute('data-id');
                   const docRef = doc(db, `artifacts//users//watchlist`, id);
                   await deleteDoc(docRef);
               }
           });
           
           // Function to handle showing the correct account form
           const showAccountForm = (formType) => {
               const loginFormSection = document.getElementById('login-section');
               const signupFormSection = document.getElementById('signup-section');
               
               loginFormSection.classList.add('hidden');
               signupFormSection.classList.add('hidden');

               if (formType === 'login') {
                   loginFormSection.classList.remove('hidden');
               } else if (formType === 'signup') {
                   signupFormSection.classList.remove('hidden');
               }
           };

           // Menu button event listener
           menuButton.addEventListener('click', () => {
               menuPanel.classList.toggle('open');
           });

           // Tab switching logic
           tabLinks.forEach(link => {
               link.addEventListener('click', (event) => {
                   event.preventDefault();
                   
                   // Update active link classes
                   tabLinks.forEach(l => {
                       l.classList.remove('bg-lime-500', 'text-black');
                       l.classList.add('bg-neutral-800', 'text-lime-500');
                   });
                   link.classList.remove('bg-neutral-800', 'text-lime-500');
                   link.classList.add('bg-lime-500', 'text-black');

                   // Hide all tabs and show the selected one
                   document.querySelectorAll('.tab-content').forEach(tab => {
                       tab.classList.remove('active');
                   });
                   const targetTabId = link.getAttribute('data-tab');
                   document.getElementById(targetTabId + '-tab').classList.add('active');

                   // Close menu
                   menuPanel.classList.remove('open');
               });
           });
           
           updateUIForAuthState();
       });
   </script>
   <style>
       /* Base styles for the entire page */
       body {
           font-family: 'Inter', sans-serif;
           background-color: #000000;
           display: flex;
           justify-content: center;
           align-items: center;
           min-height: 100vh;
           padding: 1rem;
           /* Prevents horizontal overflow on small screens */
           overflow-x: hidden;
       }
       
       /* Responsive container that adjusts to the viewport */
       .container {
           width: 100%;
           max-width: 28rem;
       }

       /* Menu button positioning */
       #menu-button {
           top: 1rem;
           right: 1rem;
           z-index: 50;
       }
       
       /* Menu panel animation and positioning */
       #menu-panel {
           top: 0;
           right: 0;
           height: 100%;
           /* Use a responsive width to avoid overflow on small screens */
           width: 0;
           transition: width 0.3s ease-in-out;
           z-index: 40;
           overflow-x: hidden;
           display: flex;
           flex-direction: column;
           justify-content: space-between;
       }
       
       #menu-panel.open {
           /* On open, set the width to a percentage of the viewport or a max value */
           width: min(80vw, 16rem);
       }

       /* Tab content visibility handling */
       .tab-content {
           display: none;
       }
       .tab-content.active {
           display: block;
       }
       .tab-link.hidden {
           display: none !important;
       }
   </style>
</head>
<body>
   <!-- Menu Button -->
   <button id="menu-button" class="fixed p-2 rounded-lg bg-black border-2 border-lime-500 shadow-md shadow-lime-500/50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500">
       <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-lime-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" />
       </svg>
   </button>

   <!-- Menu Panel -->
   <div id="menu-panel" class="fixed bg-neutral-950 shadow-xl shadow-lime-500/50 border-l-2 border-lime-500">
       <div class="p-4 flex-grow space-y-4">
           <h2 class="text-xl font-semibold text-lime-500">Menu</h2>
           <div class="space-y-2">
               <a href="#" class="tab-link block p-3 rounded-md bg-lime-500 text-black font-medium text-center shadow-md hover:bg-lime-600 transition-colors duration-200" data-tab="stocks">
                   Stocks
               </a>
               <a href="#" class="tab-link block p-3 rounded-md bg-neutral-800 text-lime-500 font-medium text-center shadow-md hover:bg-neutral-700 transition-colors duration-200" data-tab="crypto">
                   Crypto
               </a>
               <a href="#" class="tab-link hidden block p-3 rounded-md bg-neutral-800 text-lime-500 font-medium text-center shadow-md hover:bg-neutral-700 transition-colors duration-200" data-tab="portfolio">
                   Portfolio
               </a>
               <a href="#" class="tab-link hidden block p-3 rounded-md bg-neutral-800 text-lime-500 font-medium text-center shadow-md hover:bg-neutral-700 transition-colors duration-200" data-tab="watchlist">
                   Watchlist
               </a>
               <a href="#" class="tab-link block p-3 rounded-md bg-neutral-800 text-lime-500 font-medium text-center shadow-md hover:bg-neutral-700 transition-colors duration-200" data-tab="recommendations">
                   Recommendations
               </a>
               <a href="#" class="tab-link block p-3 rounded-md bg-neutral-800 text-lime-500 font-medium text-center shadow-md hover:bg-neutral-700 transition-colors duration-200" data-tab="login">
                   Login
               </a>
               <a href="#" class="tab-link block p-3 rounded-md bg-neutral-800 text-lime-500 font-medium text-center shadow-md hover:bg-neutral-700 transition-colors duration-200" data-tab="signup">
                   Sign Up
               </a>
           </div>
       </div>
       
       <!-- Logged-in section (visible when user is authenticated) -->
       <div id="logged-in-info" class="hidden p-4 space-y-2 text-center border-t border-neutral-800">
           <p class="text-sm text-lime-500 truncate">Logged in as:</p>
           <p id="logged-in-email" class="text-sm font-bold text-lime-400 truncate"></p>
           <button id="logout-button" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-black bg-neutral-400 hover:bg-neutral-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-neutral-400">
               Log Out
           </button>
       </div>
   </div>

   <!-- Main Content Container -->
   <div class="container bg-black p-6 rounded-xl shadow-lg shadow-lime-500/50">
       <!-- Stock Content -->
       <div id="stocks-tab" class="tab-content active">
           <h1 class="text-3xl font-bold text-lime-400 mb-2 text-center">Stock Price Calculator</h1>
           <p class="text-lime-500 mb-6 text-center">Find your suggested stop-loss and sell points based on a percentage.</p>

           <!-- Message box for errors or success -->
           <div id="stock-message-box" class="hidden mb-4 p-4 rounded-lg text-sm" role="alert">
               <p id="stock-message-text"></p>
           </div>

           <form id="stock-form" class="space-y-4">
               <div>
                   <label for="stock-symbol" class="block text-sm font-medium text-lime-500">Stock Symbol</label>
                   <input type="text" id="stock-symbol" placeholder="e.g., GOOGL" class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm uppercase">
               </div>
               <div>
                   <label for="stock-timeframe" class="block text-sm font-medium text-lime-500">Time Frame</label>
                   <select id="stock-timeframe" class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm">
                       <option value="realtime">Real-time (Quote)</option>
                       <option value="1min">1 Minute</option>
                       <option value="5min">5 Minutes</option>
                       <option value="15min">15 Minutes</option>
                       <option value="daily">Daily</option>
                       <option value="weekly">Weekly</option>
                       <option value="monthly">Monthly</option>
                   </select>
               </div>
               <div>
                   <label for="stock-price" class="block text-sm font-medium text-lime-500">Current Price</label>
                   <input type="number" id="stock-price" step="0.01" placeholder="Automatically fetched" readonly class="mt-1 block w-full px-3 py-2 bg-neutral-800 border border-neutral-700 text-neutral-400 rounded-md shadow-sm focus:outline-none sm:text-sm">
               </div>
               <div>
                   <label for="stock-volatility" class="block text-sm font-medium text-lime-500">Volatility Percentage</label>
                   <div class="relative mt-1 rounded-md shadow-sm">
                       <input type="number" id="stock-volatility" step="0.1" placeholder="e.g., 5" class="block w-full pr-12 px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm">
                       <div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                           <span class="text-lime-500 sm:text-sm">%</span>
                       </div>
                   </div>
               </div>
               <button type="submit" id="stock-calculate-btn" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-black bg-lime-500 hover:bg-lime-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500">
                   Calculate
               </button>
           </form>

           <!-- Stock Results Section -->
           <div id="stock-results-section" class="hidden mt-6 space-y-4">
               <h2 class="text-xl font-semibold text-lime-500">Results</h2>
               <div class="bg-neutral-900 p-4 rounded-lg shadow-inner">
                   <p class="text-sm text-neutral-400">Suggested Stop-Loss Price:</p>
                   <p id="stock-stop-loss-result" class="text-lg font-bold text-red-500 mt-1"></p>
               </div>
               <div class="bg-neutral-900 p-4 rounded-lg shadow-inner">
                   <p class="text-sm text-neutral-400">Suggested Sell Point:</p>
                   <p id="stock-sell-point-result" class="text-lg font-bold text-lime-500 mt-1"></p>
               </div>
           </div>
       </div>

       <!-- Crypto Content -->
       <div id="crypto-tab" class="tab-content">
           <h1 class="text-3xl font-bold text-lime-400 mb-2 text-center">Crypto Price Calculator</h1>
           <p class="text-lime-500 mb-6 text-center">Find your suggested stop-loss and sell points based on a percentage.</p>

           <!-- Message box for errors or success -->
           <div id="crypto-message-box" class="hidden mb-4 p-4 rounded-lg text-sm" role="alert">
               <p id="crypto-message-text"></p>
           </div>

           <form id="crypto-form" class="space-y-4">
               <div>
                   <label for="crypto-symbol" class="block text-sm font-medium text-lime-500">Crypto Symbol</label>
                   <input type="text" id="crypto-symbol" placeholder="e.g., BTC" class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm uppercase">
               </div>
               <div>
                   <label for="crypto-timeframe" class="block text-sm font-medium text-lime-500">Time Frame</label>
                   <select id="crypto-timeframe" class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm">
                       <option value="daily">Daily</option>
                       <option value="weekly">Weekly</option>
                       <option value="monthly">Monthly</option>
                   </select>
               </div>
               <div>
                   <label for="crypto-price" class="block text-sm font-medium text-lime-500">Current Price</label>
                   <input type="number" id="crypto-price" step="0.01" placeholder="Automatically fetched" readonly class="mt-1 block w-full px-3 py-2 bg-neutral-800 border border-neutral-700 text-neutral-400 rounded-md shadow-sm focus:outline-none sm:text-sm">
               </div>
               <div>
                   <label for="crypto-volatility" class="block text-sm font-medium text-lime-500">Volatility Percentage</label>
                   <div class="relative mt-1 rounded-md shadow-sm">
                       <input type="number" id="crypto-volatility" step="0.1" placeholder="e.g., 5" class="block w-full pr-12 px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm">
                       <div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                           <span class="text-lime-500 sm:text-sm">%</span>
                       </div>
                   </div>
               </div>
               <button type="submit" id="crypto-calculate-btn" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-black bg-lime-500 hover:bg-lime-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500">
                   Calculate
               </button>
           </form>

           <!-- Crypto Results Section -->
           <div id="crypto-results-section" class="hidden mt-6 space-y-4">
               <h2 class="text-xl font-semibold text-lime-500">Results</h2>
               <div class="bg-neutral-900 p-4 rounded-lg shadow-inner">
                   <p class="text-sm text-neutral-400">Suggested Stop-Loss Price:</p>
                   <p id="crypto-stop-loss-result" class="text-lg font-bold text-red-500 mt-1"></p>
               </div>
               <div class="bg-neutral-900 p-4 rounded-lg shadow-inner">
                   <p class="text-sm text-neutral-400">Suggested Sell Point:</p>
                   <p id="crypto-sell-point-result" class="text-lg font-bold text-lime-500 mt-1"></p>
               </div>
           </div>
       </div>

       <!-- Recommendations Content -->
       <div id="recommendations-tab" class="tab-content">
           <h1 class="text-3xl font-bold text-lime-400 mb-2 text-center">Market Insights</h1>
           <p class="text-lime-500 mb-6 text-center">Get a summary of recent news to help with your research.</p>
           
           <!-- Message box for recommendations errors or success -->
           <div id="recommendations-message-box" class="hidden mb-4 p-4 rounded-lg text-sm" role="alert">
               <p id="recommendations-message-text"></p>
           </div>

           <div class="space-y-4">
               <div>
                   <label for="recommendations-symbol" class="block text-sm font-medium text-lime-500">Stock or Crypto Symbol</label>
                   <input type="text" id="recommendations-symbol" placeholder="e.g., AAPL" class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm uppercase">
               </div>
               <button id="get-recommendations-btn" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-black bg-lime-500 hover:bg-lime-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500">
                   Get Insights
               </button>
           </div>
           
           <div class="mt-6">
               <div id="recommendations-output" class="p-4 bg-neutral-900 rounded-lg text-neutral-300 space-y-2">
                   <p class="text-sm text-neutral-400">Enter a symbol and click "Get Insights" to see a summary of recent news.</p>
               </div>
           </div>
       </div>

       <!-- Portfolio Content -->
       <div id="portfolio-tab" class="tab-content">
           <h1 class="text-3xl font-bold text-lime-400 mb-2 text-center">Portfolio</h1>
           <p class="text-lime-500 mb-6 text-center">Track your assets and view your total portfolio value.</p>
           
           <div class="space-y-6">
               <!-- Portfolio Section -->
               <div>
                   <div class="flex items-center justify-between mb-2">
                       <h2 class="text-xl font-semibold text-lime-500">Your Portfolio</h2>
                       <span class="text-lg font-bold text-lime-500">Total: <span id="total-portfolio-value" class="text-lime-400">.00</span></span>
                   </div>

                   <!-- Message box for portfolio errors -->
                   <div id="portfolio-message-box" class="hidden mb-4 p-4 rounded-lg text-sm" role="alert">
                       <p id="portfolio-message-text"></p>
                   </div>

                   <form id="add-portfolio-item" class="space-y-4">
                       <div class="flex space-x-2">
                           <div class="w-1/2">
                               <label for="portfolio-symbol" class="block text-sm font-medium text-neutral-400">Symbol</label>
                               <input type="text" id="portfolio-symbol" placeholder="e.g., TSLA" class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm uppercase">
                           </div>
                           <div class="w-1/2">
                               <label for="portfolio-type" class="block text-sm font-medium text-neutral-400">Type</label>
                               <select id="portfolio-type" class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm">
                                   <option value="stock">Stock</option>
                                   <option value="crypto">Crypto</option>
                               </select>
                           </div>
                       </div>
                       <div class="flex space-x-2">
                           <div class="w-1/2">
                               <label for="portfolio-quantity" class="block text-sm font-medium text-neutral-400">Quantity</label>
                               <input type="number" id="portfolio-quantity" step="0.01" placeholder="e.g., 2.5" class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm">
                           </div>
                           <div class="w-1/2">
                               <label for="portfolio-price" class="block text-sm font-medium text-neutral-400">Purchase Price</label>
                               <input type="number" id="portfolio-price" step="0.01" placeholder="e.g., 150.00" class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm">
                           </div>
                       </div>
                       <button type="submit" id="add-portfolio-btn" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-black bg-lime-500 hover:bg-lime-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500">
                           Add to Portfolio
                       </button>
                   </form>
                   
                   <ul id="portfolio-list" class="mt-4">
                       <!-- Portfolio items will be dynamically added here -->
                   </ul>
               </div>
           </div>
       </div>

       <!-- Watchlist Content -->
       <div id="watchlist-tab" class="tab-content">
           <h1 class="text-3xl font-bold text-lime-400 mb-2 text-center">Watchlist</h1>
           <p class="text-lime-500 mb-6 text-center">Track your assets.</p>
           
           <div class="space-y-6">
               <!-- Watchlist Section -->
               <div>
                   <h2 class="text-xl font-semibold text-lime-500 mb-2">Your Watchlist</h2>
                   
                   <!-- Message box for watchlist errors -->
                   <div id="watchlist-message-box" class="hidden mb-4 p-4 rounded-lg text-sm" role="alert">
                       <p id="watchlist-message-text"></p>
                   </div>

                   <form id="add-watchlist-item" class="space-y-4">
                       <div class="flex space-x-2">
                           <div class="w-1/2">
                               <label for="watchlist-symbol" class="block text-sm font-medium text-neutral-400">Symbol</label>
                               <input type="text" id="watchlist-symbol" placeholder="e.g., AMC" class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm uppercase">
                           </div>
                           <div class="w-1/2">
                               <label for="watchlist-type" class="block text-sm font-medium text-neutral-400">Type</label>
                               <select id="watchlist-type" class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm">
                                   <option value="stock">Stock</option>
                                   <option value="crypto">Crypto</option>
                               </select>
                           </div>
                       </div>
                       <button type="submit" id="add-watchlist-btn" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-black bg-lime-500 hover:bg-lime-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500">
                           Add to Watchlist
                       </button>
                   </form>
                   <ul id="watchlist-list" class="mt-4">
                       <!-- Watchlist items will be dynamically added here -->
                   </ul>
               </div>
           </div>
       </div>

       <!-- Account Content -->
       <div id="login-tab" class="tab-content">
           <h1 class="text-3xl font-bold text-lime-400 mb-2 text-center">Account</h1>
           <p class="text-lime-500 mb-6 text-center">Manage your user account.</p>

           <!-- Message box for errors or success -->
           <div id="account-message-box" class="hidden mb-4 p-4 rounded-lg text-sm" role="alert">
               <p id="account-message-text"></p>
           </div>

           <!-- Login Section -->
           <div id="login-section" class="space-y-6">
               <h2 class="text-xl font-semibold text-lime-500 mb-2">Log In</h2>
               <form id="login-form" class="space-y-4">
                   <div>
                       <label for="login-email" class="block text-sm font-medium text-lime-500">Email</label>
                       <input type="email" id="login-email" placeholder="email@example.com" required class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm">
                   </div>
                   <div>
                       <label for="login-password" class="block text-sm font-medium text-lime-500">Password</label>
                       <input type="password" id="login-password" placeholder="Password" required class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm">
                   </div>
                   <button type="submit" id="login-btn" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-black bg-lime-500 hover:bg-lime-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500">
                       Log In
                   </button>
               </form>
           </div>
       </div>
       
       <div id="signup-tab" class="tab-content">
           <h1 class="text-3xl font-bold text-lime-400 mb-2 text-center">Account</h1>
           <p class="text-lime-500 mb-6 text-center">Manage your user account.</p>

           <!-- Message box for errors or success -->
           <div id="signup-message-box" class="hidden mb-4 p-4 rounded-lg text-sm" role="alert">
               <p id="signup-message-text"></p>
           </div>
           
           <!-- Sign Up Section -->
           <div id="signup-section" class="space-y-6">
               <h2 class="text-xl font-semibold text-lime-500 mb-2">Sign Up</h2>
               <form id="signup-form" class="space-y-4">
                   <div>
                       <label for="signup-email" class="block text-sm font-medium text-lime-500">Email</label>
                       <input type="email" id="signup-email" placeholder="email@example.com" required class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm">
                   </div>
                   <div>
                       <label for="signup-password" class="block text-sm font-medium text-lime-500">Password</label>
                       <input type="password" id="signup-password" placeholder="Password" required class="mt-1 block w-full px-3 py-2 bg-neutral-900 border border-lime-500 rounded-md text-lime-400 shadow-sm focus:outline-none focus:ring-lime-500 focus:border-lime-500 sm:text-sm">
                   </div>
                   <button type="submit" id="signup-btn" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-black bg-lime-500 hover:bg-lime-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500">
                       Sign Up
                   </button>
               </form>
           </div>
           
       </div>
   </div>
</body>
</html>