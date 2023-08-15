import streamlit as st
from graphql import parse, FieldNode, GraphQLSyntaxError
import pandas as pd

def extract_fields_and_limit(query):
    document = parse(query)
    all_fields = []

    def visit_node(node, path=[], current_limit=1):
        nonlocal all_fields
        child_limit = current_limit
        if isinstance(node, FieldNode):
            for argument in node.arguments:
                if argument.name.value == "limit":
                    child_limit = int(argument.value.value) * current_limit
        if hasattr(node, "selection_set") and node.selection_set:
            for selection in node.selection_set.selections:
                new_path = path + [selection.name.value]
                if hasattr(selection, "selection_set") and selection.selection_set:
                    visit_node(selection, new_path, child_limit)
                else:
                    all_fields.append(('.'.join(new_path), child_limit))

    for definition in document.definitions:
        if hasattr(definition, "selection_set") and definition.selection_set:
            visit_node(definition)

    return all_fields

def calculate_cost(query):
    fields_with_limits = extract_fields_and_limit(query)
    total_data_points = 0  # This will hold the total number of data points requested

    for field, limit in fields_with_limits:
        total_data_points += limit

    # This will count the total data points plus the unique fields in the query
    total_cost = total_data_points + len(fields_with_limits)
    
    return total_cost, [field[0] for field in fields_with_limits], fields_with_limits

def main():
    st.title("Staking Rewards API Cost Calculator")

    query = st.text_area("Enter your GraphQL query:", """{
  assets(where: {isActive: true}, limit: 10) {
    id
    slug
    logoUrl
    metrics(where: {metricKeys: ["reward_rate"], createdAt_lt: "2023-06-28"}, limit: 10, order: {createdAt: desc}) {
      defaultValue
      createdAt
    }
  }
}
    """,height=300)

    if st.button("Calculate"):
        try:
            total_cost, fields, fields_with_limits = calculate_cost(query)

            # Displaying the output in a more structured format
            st.write("### 📊 Query Analysis")
            st.divider()
            st.metric(label="Estimated Maximum Cost", value=f"{total_cost} credits")
            st.caption("When calculating your credit needs, you should be aware that the calculations shown on this page are the maximum credits used per query. Credits are calculated based on how much data is returned rather than the theoretical number of datapoints requested. If the limit is set to 100, but only 10 entries are returned, you will only be charged for 10 entries.")
            st.divider()
            st.write("### 📌 Fields:")
            for field in fields:
                st.markdown(f"- `{field}`")
            st.divider()
            # Explanation
            st.write("### 📖 Detailed Explanation")
            # Introductory Sentence
            st.write("Below is a breakdown of how the total credits are calculated based on your query:")
            st.code(query, language='graphql')
            # Constructing the table using pandas DataFrame
            calculations = {
                "Field": [],
                "Calculation": [],
                "Result": []
            }

            sum_of_credits = 0
            for field, limit in fields_with_limits:
                calculations["Field"].append(field)
                calculations["Calculation"].append(f"1 x {limit}")
                calculations["Result"].append(f"{limit} credits")
                sum_of_credits += limit

            df = pd.DataFrame(calculations)
            st.table(df)

            st.caption("**Field**: Represents the specific data point or attribute requested in the query.")
            st.caption("**Calculation**: Indicates how many times a particular field will be returned based on the query. The `1 x [limit]` format shows that for each entry in the response, this field will be returned once. The `[limit]` specifies the max number of entries this field will be returned for.")
            st.caption("**Result**: Total credits consumed by querying this field for the specified limit.")

            st.divider()
            total_fields = len(fields)
            st.latex(r"\text{Total Fields in Query} = " + str(total_fields))
            st.latex(r"\text{Sum of Credits} = \sum \text{credits from each field} = " + str(sum_of_credits))
            st.latex(r"\text{Total Credits Consumed} = \text{Sum of Credits} + \text{Total Fields in Query}")
            st.latex(r"= " + str(sum_of_credits) + " + " + str(total_fields) + " = " + str(total_cost))
            st.caption("The formula above shows how the total credits consumed is calculated. The sum of credits is the total number of credits consumed by all fields in the query. The total fields in query is the number of unique fields in the query. The total credits consumed is the sum of credits plus the total fields in query.")

        except GraphQLSyntaxError:
                st.error("There seems to be a syntax error in your GraphQL query. Please check and try again.")
            
        except Exception as e:
            st.error(f"Error: {e}")

    st.markdown('little helper created by [**@0xfabs**](https://twitter.com/0xfabs) | [**Staking Rewards API**](https://stakingrewards.typeform.com/apply-api)')



if __name__ == "__main__":
    main()
