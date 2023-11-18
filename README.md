# llm_web
Plugin for [llm](https://llm.datasette.io/) by the great [simonw](https://simonwillison.net/) to add a simple langchain agent that searches the web.

## Note
* to install: `llm install llm-web`
* to run: `llm chat -m web`
* Very early stage, done mostly while procrastinating work. Will improve a lot.

## TODO
* tell simonw
* make autonomous agent more stable
* find a way to implement streaming
* *later* use griptape instead of langchain when they implement their search?

## DEMO (cherry picked)
Question was: `Use 'complicated' to look up the age of the UK prime minister and of Angela Merkel, multiply them together then divide by the age of the wife of Barrack Obama.`
Total cost: 14901 tokens, so $0.015 using ChatGPT-3.5-turbo-1106

```
Chatting with web
Type 'exit' or 'quit' to exit
Type '!multi' to enter multiple lines, then '!end' to finish
> Use 'complicated' to look up the age of the UK prime minister and of Angela Merkel, multiply them together then divide by the age of the wife of Barrack Obama.


> Entering new AgentExecutor chain...
'''json
{
    "action": "complicated",
    "action_input": "((age of UK prime minister) * (age of Angela Merkel)) / (age of the wife of Barack Obama)"
}
'''

> Entering new LLMChain chain...
Prompt after formatting:

I want to answer the question '((age of UK prime minister) * (age of Angela Merkel)) / (age of the wife of Barack Obama)'. Please generate up to 5 steps needed to answer that question.
Don't worry about intermediate steps seeming too complicated, we can subdivide them later on.
If the question is already phrased as a series of steps, just rewrite into the appropriate format.
Use your tools to answer the question.

ALWAYS answer using the appropriate format.
APPROPRIATE FORMAT: one step per line, without enumeration.

Example of format:
'''
Find the name of the owner of MacDonald's
Find his age
Multiply it by 4
Return the answer
'''

Your turn now:


> Finished chain.
Executing complicated task: 0step [00:00, ?step/s]The end goal it to answer this: '((age of UK prime minister) * (age of Angela Merkel)) / (age of the wife of Barack Obama)'.

Here is the task planning:
1. Find the current age of the UK prime minister. TODO
2. Find the current age of Angela Merkel. LATER
3. Find the current age of the wife of Barack Obama. LATER
4. Multiply the age of the UK prime minister by the age of Angela Merkel. LATER
5. Divide the result by the age of the wife of Barack Obama. LATER

Your current task is #1


> Entering new AgentExecutor chain...
'''json
{
    "action": "duckduckgo_search",
    "action_input": "current age of UK prime minister"
}
'''
Observation: The first prime minister of the current United Kingdom of Great Britain and Northern Ireland upon its effective creation in 1922 (when 26 Irish counties seceded and created the Irish Free State) was Bonar Law, [10] although the country was not renamed officially until 1927, when Stanley Baldwin was the serving prime minister. [11] Rishi Sunak is the current Prime Minister of the United Kingdom.He is one of the wealthiest politicians in Westminster, Britain as well as the first leader of colour. He replaced the former PM Liz ... The current monarch is King Charles III, who ascended the throne on 8 September 2022, upon the death of his mother, Queen Elizabeth II . The monarch and their immediate family undertake various official, ceremonial, diplomatic and representational duties. Jeremy Hunt, the current finance minister, held the office from 2018-2019, with former prime minister Johnson in situ for two years from July 2016 to July 2018. Vikki Velasquez Rishi Sunak is a former investment banker and hedge fund manager turned politician. He was appointed as prime minister of the United Kingdom by his peers in October 2022 after...
Thought:'''json
{
    "action": "duckduckgo_search",
    "action_input": "Rishi Sunak age"
}
'''
Observation: (1980-) Who Is Rishi Sunak? Following a successful early career in finance, Rishi Sunak entered Parliament as a Conservative MP from Richmond in 2015. Named Chancellor of the Exchequer just... Sunak became the first non-White person to lead the country and, at age 42, the youngest to take on the role in more than a century. Like most politicians, Sunak is revered by some and... Rishi Sunak and his wife, Akshata Murty, boarding a plane in Tokyo to travel to Hiroshima for the G7 Summit in Japan in May 2023. Photograph: Stefan Rousseau/PA The details-obsessed technocrat. general knowledge Current GK Rishi Sunak Biography: Birth, Age, Parents, Education, Political Career, Net Worth, And More Rishi Sunak has become the first Indian-origin Prime Minister of... Prime Miniser Rishi Sunak is the first Asian leader the UK has ever had and is also one of the youngest - but what else do we need to know about him? Background, age and where he's from revealed. Rishi Sunak officially became the UK's new prime minister following Liz Truss ' shock resignation after just 45 days.
Thought:'''json
{
    "action": "Final Answer",
    "action_input": "42"
}
'''

> Finished chain.
Executing complicated task: 1step [00:09,  9.65s/step]The end goal it to answer this: '((age of UK prime minister) * (age of Angela Merkel)) / (age of the wife of Barack Obama)'.

Here is the task planning:
1. Find the current age of the UK prime minister. Done: '42'
2. Find the current age of Angela Merkel. TODO
3. Find the current age of the wife of Barack Obama. LATER
4. Multiply the age of the UK prime minister by the age of Angela Merkel. LATER
5. Divide the result by the age of the wife of Barack Obama. LATER

Your current task is #2


> Entering new AgentExecutor chain...
'''json
{
    "action": "Wikipedia",
    "action_input": "Angela Merkel"
}
'''
Observation: Page: Angela Merkel
Summary: Angela Dorothea Merkel  (German: [aŋˈɡeːla doʁoˈteːa ˈmɛʁkl̩] ; née Kasner; born 17 July 1954) is a German former politician and scientist who served as chancellor of Germany from 2005 to 2021. A member of the Christian Democratic Union (CDU), she previously served as Leader of the Opposition from 2002 to 2005 and as Leader of the Christian Democratic Union from 2000 to 2018. Merkel was the first female chancellor of Germany. During her chancellorship, Merkel was frequently referred to as the de facto leader of the European Union (EU) and the most powerful woman in the world. Beginning in 2016, she was often described as the leader of the free world.Merkel was born in Hamburg in then-West Germany. Her family moved to East Germany when she was an infant. Merkel obtained a doctorate in quantum chemistry in 1986 and worked as a research scientist until 1989. She then entered politics in the wake of the Revolutions of 1989, briefly serving as deputy spokeswoman for the first democratically elected government of East Germany led by Lothar de Maizière. Following German reunification in 1990, Merkel was elected to the Bundestag for the state of Mecklenburg-Vorpommern. As the protégée of chancellor Helmut Kohl, Merkel was appointed as Minister for Women and Youth in 1991, later becoming Minister for the Environment, Nature Conservation and Nuclear Safety in 1994. After the CDU lost the 1998 federal election, Merkel was elected general secretary of the party. She then became the party's first female leader, and the first female Leader of the Opposition two years later.
Following the 2005 federal election, Merkel was elected chancellor, leading a grand coalition consisting of the CDU, the Christian Social Union (CSU), and the Social Democratic Party of Germany (SPD). She was the first woman to be elected chancellor, and the first chancellor of reunified Germany to have been raised in the former East Germany. In the 2009 federal election, the CDU obtained the largest share of the vote, and Merkel subsequently formed a coalition government with the Free Democratic Party (FDP), an alliance more favourable to the CDU than the grand coalition. In the 2013 federal election, the CDU won a landslide victory and formed a second grand coalition with the SPD, after the FDP lost all of its representation in the Bundestag. In the 2017 federal election, Merkel led the CDU to become the largest party for the fourth time, resulting in the formation of a third grand coalition with the SPD.In foreign policy, Merkel emphasised international cooperation, both in the context of the EU and NATO, and the strengthening of transatlantic economic relations. In 2008, Merkel served as president of the European Council and played a central role in the negotiation of the Treaty of Lisbon and the Berlin Declaration. Merkel's governments managed the global 2007–2008 financial crisis and the European debt crisis. She negotiated the 2008 European Union stimulus plan, which focused on infrastructure spending and public investment to counteract the Great Recession. In domestic policy, Merkel's Energiewende program supported the development of renewable energy sources and eventually phased out the use of nuclear power in Germany. Reforms to the Bundeswehr, health care reform, the 2010s European migrant crisis, and the COVID-19 pandemic were major issues during her chancellorship. Merkel stepped down as leader of the CDU and did not seek a fifth term as chancellor in the 2021 federal election.

Page: Family of Angela Merkel
Summary: The family of Angela Merkel, the former Chancellor of Germany, is of German and Polish descent. Merkel was born Angela Dorothea Kasner on 17 July 1954
in Hamburg. The Kasner name is derived from Jan Kaźmierczak, a Pole from Poznań who lived in the 18th century. Merkel's grandfather changed the name to Kasner in 1930. Merkel has been married twice, and kept the name of her first husband, Ulrich Merkel. Angela Merkel's
Thought:'''json
{
    "action": "Final Answer",
    "action_input": "67"
}
'''

> Finished chain.
Executing complicated task: 2step [00:16,  8.06s/step]The end goal it to answer this: '((age of UK prime minister) * (age of Angela Merkel)) / (age of the wife of Barack Obama)'.

Here is the task planning:
1. Find the current age of the UK prime minister. Done: '42'
2. Find the current age of Angela Merkel. Done: '67'
3. Find the current age of the wife of Barack Obama. TODO
4. Multiply the age of the UK prime minister by the age of Angela Merkel. LATER
5. Divide the result by the age of the wife of Barack Obama. LATER

Your current task is #3


> Entering new AgentExecutor chain...
'''json
{
    "action": "Wikipedia",
    "action_input": "Michelle Obama"
}
'''
Observation: Page: Michelle Obama
Summary: Michelle LaVaughn Robinson Obama (born January 17, 1964) is an American attorney and author who served as the first lady of the United States from 2009 to 2017, being married to former president Barack Obama.
Raised on the South Side of Chicago, Obama is a graduate of Princeton University and Harvard Law School. In her early legal career, she worked at the law firm Sidley Austin where she met her future husband. She subsequently worked in nonprofits and as the associate dean of Student Services at the University of Chicago. Later she served as, vice president for Community and External Affairs of the University of Chicago Medical Center. Michelle married Barack in 1992 and they have two daughters.
Obama campaigned for her husband's presidential bid throughout 2007 and 2008, delivering a keynote address at the 2008 Democratic National Convention. She has subsequently delivered acclaimed speeches at the 2012, 2016, and 2020 conventions. As first lady, Obama served as a role model for women and worked as an advocate for poverty awareness, education, nutrition, physical activity, and healthy eating. She supported American designers and was considered a fashion icon. Obama was the first African-American woman to serve as first lady.
After her husband's presidency, Obama's influence has remained high. In 2020, she topped Gallup's poll of the most admired woman in America for the third year running.

Page: Family of Barack Obama
Summary: The family of Barack Obama, the 44th president of the United States, is a prominent American family active in law, education, activism and politics. Obama's immediate family circle was the first family of the United States from 2009 to 2017, and are the first such family of African-American descent. His immediate family includes his wife Michelle Obama and daughters Malia and Sasha.
Obama's wider ancestry is made up of people of Kenyan (Luo), African-American, and Old Stock American (including originally English, Scots-Irish, Welsh, German, and Swiss) ancestry.

Page: First Lady Michelle Obama (painting)
Summary: First Lady Michelle Obama, initially titled Michelle LaVaughn Robinson Obama, is a portrait of former First Lady of the United States Michelle Obama, painted by the artist Amy Sherald. Unveiled in 2018, it hangs in the National Portrait Gallery (NPG) in Washington, D.C. The six-by-five-foot (1.8 by 1.5 m) oil-on-linen painting shows Obama, rendered in Sherald's signature grisaille, resting her chin lightly on her hand, as a geometric print dress flows outward filling the frame against a sky-blue background.
Praised by critics and immensely popular with museum visitors, the National Portrait Gallery's attendance doubled in the two years after the unveiling of Sherald's portrait along with Kehinde Wiley's portrait of President Barack Obama. Museum director Kim Sajet credits Sherald and Wiley with reinvigorating the genre of portrait painting. Sherald and Wiley were also the first African American artists to receive commissions for National Portrait Gallery presidential portraits.


Thought:'''json
{
    "action": "Final Answer",
    "action_input": "57"
}
'''

> Finished chain.
Executing complicated task: 3step [00:21,  6.50s/step]The end goal it to answer this: '((age of UK prime minister) * (age of Angela Merkel)) / (age of the wife of Barack Obama)'.

Here is the task planning:
1. Find the current age of the UK prime minister. Done: '42'
2. Find the current age of Angela Merkel. Done: '67'
3. Find the current age of the wife of Barack Obama. Done: '57'
4. Multiply the age of the UK prime minister by the age of Angela Merkel. TODO
5. Divide the result by the age of the wife of Barack Obama. LATER

Your current task is #4


> Entering new AgentExecutor chain...
'''json
{
    "action": "Final Answer",
    "action_input": "2814"
}
'''

> Finished chain.
Executing complicated task: 4step [00:23,  4.64s/step]The end goal it to answer this: '((age of UK prime minister) * (age of Angela Merkel)) / (age of the wife of Barack Obama)'.

Here is the task planning:
1. Find the current age of the UK prime minister. Done: '42'
2. Find the current age of Angela Merkel. Done: '67'
3. Find the current age of the wife of Barack Obama. Done: '57'
4. Multiply the age of the UK prime minister by the age of Angela Merkel. Done: '2814'
5. Divide the result by the age of the wife of Barack Obama. TODO

Your current task is #5


> Entering new AgentExecutor chain...
'''json
{
    "action": "Final Answer",
    "action_input": "49.26315789473684"
}
'''

> Finished chain.
Executing complicated task: 5step [00:27,  5.42s/step]


> Entering new AgentExecutor chain...
'''json
{
    "action": "Final Answer",
    "action_input": "49.26315789473684"
}
'''

> Finished chain.

Observation: 49.26315789473684
Thought:'''json
{
    "action": "Final Answer",
    "action_input": "49.26315789473684"
}
'''

> Finished chain.

Token so far: 14901 or $0.015279
49.26315789473684
>

```
