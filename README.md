https://blog.langchain.dev/langgraph-multi-agent-workflows/
https://langchain-ai.github.io/langgraph/concepts/multi_agent/#supervisor-tool-calling
Multi-agent Systems
Build language agents as graphs
 https://python.langchain.com/docs/how_to/structured_output/
 ****************************
 from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from playwright.async_api import async_playwright
import asyncio
import nest_asyncio

# Apply nest_asyncio for Jupyter compatibility
nest_asyncio.apply()

class ShoppingState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    bigbasket_data: dict
    blinkit_data: dict
    browser: dict
    error: str | None
    selected_platform: str | None
    login_status: dict  # Track login state and OTP
    cart_status: str    # Track cart status

async def access_cart(page):
    """Click on cart icon to access cart"""
    try:
        # Click on cart icon using the SVG path
        cart_button = await page.wait_for_selector('path[d*="M0 0h24v24H0z"]')
        await cart_button.click()
        return True
    except Exception as e:
        print(f"Error accessing cart: {str(e)}")
        return False

async def login_user(page, phone_number):
    """Handle user login"""
    try:
        # Find and fill phone number input
        phone_input = await page.wait_for_selector('input#multiform')
        await phone_input.fill(phone_number)
        return True
    except Exception as e:
        print(f"Error during login: {str(e)}")
        return False

async def verify_otp(page, otp):
    """Handle OTP verification"""
    try:
        # Find all OTP input fields
        otp_inputs = await page.query_selector_all('input[type="number"]')
        
        # Fill each digit of OTP
        for i, digit in enumerate(otp):
            if i < len(otp_inputs):
                await otp_inputs[i].fill(digit)
        
        # Find and click verify button
        verify_button = await page.wait_for_selector('button[type="submit"]')
        await verify_button.click()
        return True
    except Exception as e:
        print(f"Error verifying OTP: {str(e)}")
        return False

async def add_to_cart(page, product_url, platform):
    """Add product to cart based on platform"""
    try:
        if platform == "bigbasket":
            await page.goto(product_url)
            add_to_cart_button = await page.wait_for_selector('button.Button-sc-1dr2sn8-0.CTA___StyledButton-sc-yj3ixq-5.kYQsWi.bYACar')
            await add_to_cart_button.click()
            return True
        elif platform == "blinkit":
            await page.goto(product_url)
            add_to_cart_button = await page.wait_for_selector('div.AddToCart__UpdatedButtonContainer-sc-17ig0e3-0.lmopxc')
            await add_to_cart_button.click()
            return True
        return False
    except Exception as e:
        print(f"Error adding to cart: {str(e)}")
        return False



# Initialize LLM
llm = ChatGroq(model="llama-3.2-90b-vision-preview", api_key="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")

async def setup_browser():
    playwright = await async_playwright().start()
    browser = await playwright.webkit.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    return {
        'playwright': playwright,
        'browser': browser,
        'context': context,
        'page': page
    }

# Node functions
async def initialize_browser(state: ShoppingState) -> ShoppingState:
    """Initialize browser and add to state"""
    try:
        browser_instance = await setup_browser()
        return {
            **state,
            "browser": browser_instance,
            "messages": [{
                "role": "assistant",
                "content": "Browser initialized successfully. Ready to search."
            }]
        }
    except Exception as e:
        return {
            **state,
            "error": f"Browser initialization failed: {str(e)}",
            "messages": [{
                "role": "assistant",
                "content": f"Error initializing browser: {str(e)}"
            }]
        }

async def scrape_bigbasket(state: ShoppingState) -> ShoppingState:
    """
    Scrape BigBasket products using the updated HTML structure
    """
    try:
        page = state['browser']['page']
        await page.goto(f"https://www.bigbasket.com/ps/?q={state['query']}")
        
        products = await page.evaluate('''() => {
            const items = document.querySelectorAll('.PaginateItems___StyledLi-sc-1yrbjdr-0');
            return Array.from(items).slice(0, 3).map(item => {
                const nameLink = item.querySelector('a[target="_blank"]');
                const imageElement = item.querySelector('img');
                const priceElement = item.querySelector('.price'); // You'll need to update this selector based on actual price element
                
                return {
                    name: imageElement?.getAttribute('title') || '',
                    image_url: imageElement?.getAttribute('src') || '',
                    product_url: nameLink?.getAttribute('href') || '',
                    price: priceElement?.innerText || '',
                    details: item.innerText
                };
            });
        }''')
        
        # Clean up the data
        cleaned_products = []
        for product in products:
            if product['product_url'].startswith('/'):
                product['product_url'] = f"https://www.bigbasket.com{product['product_url']}"
            cleaned_products.append(product)
        
        return {
            **state,
            "bigbasket_data": cleaned_products,
            "messages": [{
                "role": "assistant",
                "content": f"Successfully scraped {len(cleaned_products)} products from BigBasket"
            }]
        }
    except Exception as e:
        return {
            **state,
            "error": f"BigBasket scraping failed: {str(e)}",
            "messages": [{
                "role": "assistant", 
                "content": f"Error scraping BigBasket: {str(e)}"
            }]
        }

async def scrape_blinkit(state: ShoppingState) -> ShoppingState:
    """Scrape Blinkit products with updated selectors"""
    try:
        page = state['browser']['page']
        print(page)
        await page.goto(f"https://blinkit.com/s/?q={state['query']}")
        # await page.wait_for_load_state('networkidle')
        
        # Wait for product container
        await page.wait_for_selector('.ProductsContainer__SearchProductsListContainer-sc-1k8vkvc-1', timeout=5000)
        # Extract product details using the updated structure
        products = await page.evaluate('''() => {
            const items = document.querySelectorAll('[data-test-id="plp-product"]');
            return Array.from(items).slice(0, 3).map(item => {
                // Get product title
                const titleElement = item.querySelector('.Product__UpdatedTitle-sc-11dk8zk-9');
                const title = titleElement ? titleElement.innerText : '';
                
                // Get price
                const priceElement = item.querySelector('.Product__UpdatedPriceAndAtcContainer-sc-11dk8zk-10 div div');
                const price = priceElement ? priceElement.innerText : '';
                
                // Get original price if available (for discounted items)
                const originalPriceElement = item.querySelector('[style*="text-decoration-line: line-through"]');
                const originalPrice = originalPriceElement ? originalPriceElement.innerText : '';
                
                // Get quantity/weight
                const quantityElement = item.querySelector('.plp-product__quantity--box');
                const quantity = quantityElement ? quantityElement.innerText : '';
                
                // Get offer if available
                const offerElement = item.querySelector('.Product__UpdatedOfferTitle-sc-11dk8zk-2');
                const offer = offerElement ? offerElement.innerText : '';
                
                // Get delivery time
                const deliveryElement = item.querySelector('[style*="text-transform: uppercase"]');
                const deliveryTime = deliveryElement ? deliveryElement.innerText : '';
                
                // Get image URL
                const imageElement = item.querySelector('img[alt]');
                const imageUrl = imageElement ? imageElement.src : '';
                
                return {
                    name: title,
                    price: price,
                    originalPrice: originalPrice,
                    quantity: quantity,
                    offer: offer,
                    deliveryTime: deliveryTime,
                    imageUrl: imageUrl,
                    details: `${title} - ${quantity} - ${price}${originalPrice ? ' (Original: ' + originalPrice + ')' : ''}${offer ? ' | ' + offer : ''}`
                };
            });
        }''')
        print(products)
        return {
            **state,
            "blinkit_data": products,
            "messages": [{
                "role": "assistant",
                "content": f"Found {len(products)} products on Blinkit with details including prices, quantities, and offers"
            }]
        }
    except Exception as e:
        return {
            **state,
            "error": f"Blinkit scraping failed: {str(e)}",
            "messages": [{
                "role": "assistant",
                "content": f"Error scraping Blinkit: {str(e)}"
            }]
        }
async def handle_order_process(state: ShoppingState, phone_number: str = None, otp: str = None) -> dict:
    """Handle the complete order process"""
    try:
        page = state['browser']['page']
        
        # Step 1: Access cart
        cart_accessed = await access_cart(page)
        if not cart_accessed:
            return {"success": False, "message": "Could not access cart"}
        
        # Step 2: Login (if phone number provided)
        if phone_number:
            login_success = await login_user(page, phone_number)
            if not login_success:
                return {"success": False, "message": "Login failed"}
        
        # Step 3: Verify OTP (if provided)
        if otp:
            otp_success = await verify_otp(page, otp)
            if not otp_success:
                return {"success": False, "message": "OTP verification failed"}
        
        return {"success": True, "message": "Order process completed successfully"}
    
    except Exception as e:
        return {"success": False, "message": f"Error in order process: {str(e)}"}


async def generate_comparison(state: ShoppingState) -> ShoppingState:
    """Generate comparison report using LLM"""
    try:
        prompt = f"""
        Compare the following products from BigBasket and Blinkit:
        
        BigBasket Products:
        {state['bigbasket_data']}
        
        Blinkit Products:
        {state['blinkit_data']}
        
        Please provide a detailed comparison including:
        1. Price comparison for similar products (in Single line)
        2. Best deals/offers
        3. Recommendation based on price and value
        4. At the end, ask if they would like to add any items to cart

        Important
        - Write the whole thing very concisely and short
        - End with asking if they want to add items to cart
        """
        
        response = await llm.ainvoke(prompt)
        
        return {
            **state,
            "messages": [{
                "role": "assistant",
                "content": response.content
            }]
        }
    except Exception as e:
        return {
            **state,
            "error": f"Comparison generation failed: {str(e)}",
            "messages": [{
                "role": "assistant",
                "content": f"Error generating comparison: {str(e)}"
            }]
        }

async def add_to_cart_handler(state: ShoppingState, platform: str, product_index: int) -> bool:
    """Handle adding products to cart"""
    try:
        products = state['bigbasket_data'] if platform == 'bigbasket' else state['blinkit_data']
        if 0 <= product_index < len(products):
            product = products[product_index]
            result = await add_to_cart(state['browser']['page'], product['product_url'], platform)
            return result
        return False
    except Exception as e:
        print(f"Error in add_to_cart_handler: {str(e)}")
        return False

# Create and configure the graph
def create_shopping_graph():
    graph = StateGraph(ShoppingState)
    
    # Add nodes
    graph.add_node("initialize", initialize_browser)
    graph.add_node("bigbasket", scrape_bigbasket)
    graph.add_node("blinkit", scrape_blinkit)
    graph.add_node("compare", generate_comparison)
    
    # Define edges
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "bigbasket")
    graph.add_edge("bigbasket", "blinkit")
    graph.add_edge("blinkit", "compare")
    graph.add_edge("compare", END)
    
    return graph.compile()

# Main execution function
async def compare_products(query: str):
    initial_state = ShoppingState(
        messages=[],
        query=query,
        bigbasket_data={},
        blinkit_data={},
        browser={},
        error=None,
        selected_platform=None
    )
    
    graph = create_shopping_graph()
    final_state = await graph.ainvoke(initial_state)
    return final_state

# Synchronous wrapper for easy usage
def run_comparison(query: str):
    async def _run():
        return await compare_products(query)
    return asyncio.get_event_loop().run_until_complete(_run())

# <div class="bg-black px-12 py-6 rounded-r-sm"><span class="Label-sc-15v1nk5-0 gJxZPQ text-lg leading-xxl font-bold text-silverSurfer-100">Login/ Sign up</span><p class="text-sm leading-xxs font-regular text-silverSurfer-100 pb-1.5">Using OTP</p><div class="border border-darkOrange-500 rounded-lg w-10.5"></div><form class="w-71.5 pt-8.1 pb-2.5"><div class="relative flex flex-col pb-12"><input id="multiform" name="multiform" placeholder="Enter Phone number/ Email Id" class="peer p-2.5 text-md leading-base font-regular text-darkOnyx-700 rounded-2xs focus:outline-none focus:shadow-outline border-darkOnyx-400 border placeholder-transparent" value=""><label for="multiform" class="absolute left-0 -top-3.5 text-xs leading-xxs font-regular text-silverSurfer-800 peer-placeholder-shown:text-md peer-placeholder-shown:text-silverSurfer-900 peer-placeholder-shown:top-3 peer-placeholder-shown:pl-2.5 transition-all peer-placeholder-shown:leading-base">Enter Phone number/ Email Id</label></div><button type="submit" class="w-71.5
