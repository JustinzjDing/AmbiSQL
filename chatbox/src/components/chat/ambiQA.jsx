import React, { useState, useEffect } from "react";

const SQLAmbiguityResolver = () => {
  const [question, setQuestion] = useState(
    "How many drivers born after the end of Vietnam War have been ranked 2?"
  );
  const [dbDialect, setDbDialect] = useState("SQLite");
  const [dbUsed, setDBUsed] = useState("formula_1");
  const [ambiguities, setAmbiguities] = useState([]);
  const [clarificationList, setClarificationList] = useState([]);
  const [sessionId, setSessionId] = useState(null); //session_id
  const [additionalInfo, setAdditionalInfo] = useState("");
  const [showComparison, setShowComparison] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [schemaLinkingResult, setSchemaLinkingResult] = useState([]);

  const [isSQLReady, setIsSQLReady] = useState(false);
  const [rawSQL, setRawSQL] = useState(null);
  const [rawResult, setRawResult] = useState(null);
  const [clarifiedSQL, setClarifiedSQL] = useState(null);
  const [clarifiedResult, setClarifiedResult] = useState(null);

  const [isDetectingAmbiguity, setIsDetectingAmbiguity] = useState(false);
  const [isTranslatingSQL, setIsTranslatingSQL] = useState(false);

  const examples = [
    {
      id: 1,
      question:
        "How many drivers born after the end of Vietnam War have been ranked 2?",
      db_name: "formula_1",
      dialect: "SQLite",
    },
    {
      id: 2,
      question:
        "Name all drivers in the 2010 Singapore Grand Prix order by their position stands.",
      db_name: "formula_1",
      dialect: "SQLite",
    },
    {
      id: 3,
      question:
        "Give the name of the league had the most matches end as draw in the 2016 season?",
      db_name: "european_football_2",
      dialect: "SQLite",
    },
    {
      id: 4,
      question: "List top 5 popular tags's viewcount.",
      db_name: "codebase_community",
      dialect: "SQLite",
    },
    {
      id: 5,
      question:
        "How many transactions taken place in the gas station in the Czech Republic are with a price of over 45 US dollars?",
      db_name: "debit_card_specializing",
      dialect: "SQLite",
    },
  ];

  useEffect(() => {
    if (ambiguities.length > 0) {
      setClarificationList(
        ambiguities.map((question) => ({
          question,
          answer: "",
        }))
      );
    }
  }, [ambiguities]);

  const handleExampleSelect = (selectedExample) => {
    setQuestion(selectedExample.question);
    setDBUsed(selectedExample.db_name);
    setDbDialect(selectedExample.dialect);

    // reset related states
    setAmbiguities([]);
    setClarificationList([]);
    setAdditionalInfo("");
    setShowComparison(false);
    setIsLoading(false);
    setSchemaLinkingResult([]);
    setSessionId(null);
    setIsSQLReady(false);
    setRawSQL(null);
    setRawResult(null);
    setClarifiedSQL(null);
    setClarifiedResult(null);
  };

  const handleSubmit = async () => {
    setIsDetectingAmbiguity(true); // Set ambiguity detection signal
    setIsLoading(true);
    setShowComparison(false); // Clear previous comparison state
    setRawSQL(null); // Reset previous SQL/results
    setRawResult(null);
    setClarifiedSQL(null);
    setClarifiedResult(null);
    setIsSQLReady(false);
    setAmbiguities([]); // Reset ambiguities
    setClarificationList([]); // Reset clarification list
    setAdditionalInfo(""); // Reset additional info

    try {
      const response = await fetch("http://localhost:8765/api/sql/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: question,
          dialect: dbDialect,
          db: dbUsed,
          session_id: sessionId, // Send current sessionId
        }),
      });

      if (!response.ok) {
        throw new Error(`Network response was not ok: ${response.statusText}`);
      }

      const data = await response.json();
      console.log("Analyze response data:", data);

      if (data.session_id) {
        setSessionId(data.session_id);
        console.log("Session ID received:", data.session_id);
      } else {
        console.warn("No session_id received from /analyze endpoint.");
      }
      setIsDetectingAmbiguity(false);

      if (data?.suggested_schema) {
        setSchemaLinkingResult(data.suggested_schema);
      } else {
        setSchemaLinkingResult([]);
        console.warn("No suggested_schema received in response.");
      }
      setAmbiguities(data.ambiguities || []); // Ensure it's an array

      setTimeout(() => {
        setIsLoading(false);
        setIsDetectingAmbiguity(false);
      }, 500);
    } catch (error) {
      console.error("Error during handleSubmit:", error);
      alert(
        `Failed to process the query: ${error.message}. Please check console for details.`
      );
      setIsDetectingAmbiguity(false);
      setIsLoading(false);
    }
  };

  const handleClarifySumbit = async () => {
    setIsTranslatingSQL(true);

    if (!sessionId) {
      alert(
        "Please submit the initial question first to start a session before clarifying."
      );
      setIsTranslatingSQL(false);
      return;
    }
    console.log("Submitting clarification with:", {
      clarificationList,
      additionalInfo,
      sessionId,
    });

    try {
      const response = await fetch("http://localhost:8765/api/sql/solve", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
          clarificationList: clarificationList,
          additional_info: additionalInfo,
        }),
      });

      if (!response.ok) {
        throw new Error(`Network response was not ok: ${response.statusText}`);
      }

      const data = await response.json();
      console.log("Solve response data:", data);

      if (data.is_clarified === "True") {
        setIsSQLReady(true);
        setRawSQL(data.sql_statement_raw);
        setClarifiedSQL(data.sql_statement_clarified);
      } else {
        setIsTranslatingSQL(false);
        setAmbiguities(data.ambiguities || []); //
      }
    } catch (error) {
      console.error("Error during handleClarifySubmit:", error);
      alert(
        `Failed to clarify: ${error.message}. Please check console for details.`
      );
      setIsLoading(false);
    } finally {
      setIsTranslatingSQL(false);
    }
  };

  const handleComparison = async () => {
    setShowComparison(true);
  };
  const handleClear = () => {
    setQuestion(
      "How many drivers born after the end of Vietnam War have been ranked 2?"
    );
    setDbDialect("SQLite");
    setDBUsed("formula_1");
    setAmbiguities([]);
    setClarificationList([]);
    setAdditionalInfo("");
    setShowComparison(false);
    setIsLoading(false);
    setSchemaLinkingResult([]);
    setSessionId(null);
    setIsSQLReady(false);
    setRawSQL(null);
    setRawResult(null);
    setClarifiedSQL(null);
    setClarifiedResult(null);
  };

  return (
    <div className="dashboard">
      <div className="layout-container">
        {/* Left Column - Top Card */}
        <div className="card user-input-card">
          <div className="form-group">
            <label>Question</label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={1}
              placeholder="Enter your SQL-related question..."
            />
          </div>

          <div className="db-selector-group">
            <div className="form-group">
              <label>DB Dialect</label>
              <select
                value={dbDialect}
                onChange={(e) => setDbDialect(e.target.value)}
              >
                <option value="SQLite">SQLite</option>
                <option value="MySQL">MySQL</option>
                <option value="PostgreSQL">PostgreSQL</option>
                <option value="SQL Server">SQL Server</option>
                <option value="Oracle">Oracle</option>
              </select>
            </div>

            <div className="form-group">
              <label>DB used</label>
              <select
                value={dbUsed}
                onChange={(e) => setDBUsed(e.target.value)}
              >
                <option value="formula_1">formula_1</option>
                <option value="california_schools">california_schools</option>
                <option value="european_football_2">european_football_2</option>
                <option value="codebase_community">codebase_community</option>
                <option value="superhero">superhero</option>
              </select>
            </div>
          </div>

          <div className="actions">
            <button className="clear-btn" onClick={handleClear}>
              Clear
            </button>
            <button className="submit-btn" onClick={handleSubmit}>
              Submit
            </button>
          </div>
        </div>

        {/* 2. Ambiguity Resolve Card */}
        <div className="card interaction-card">
          {isDetectingAmbiguity ? (
            <div className="loading-overlay">
              <div className="loading-content">
                <div className="spinner"></div>
                <span>Waiting for ambiguity detection</span>
              </div>
            </div>
          ) : (
            <>
              <div className="clarifications">
                {ambiguities.length > 0 ? (
                  <>
                    {ambiguities.map((questionObj, questionIndex) => (
                      <div className="clarification-item" key={questionIndex}>
                        <p>{questionObj.question}</p>
                        <select
                          value={clarificationList[questionIndex]?.answer || ""}
                          onChange={(e) => {
                            const newList = [...clarificationList];
                            newList[questionIndex] = {
                              ...newList[questionIndex],
                              answer: e.target.value,
                            };
                            setClarificationList(newList);
                          }}
                        >
                          <option value="" disabled>
                            Please select an answer
                          </option>
                          {(questionObj.choices || []).map(
                            (choice, choiceIndex) => (
                              <option key={choiceIndex} value={choice}>
                                {choice}
                              </option>
                            )
                          )}
                        </select>
                      </div>
                    ))}
                    <div className="clarification-item">
                      <label>Additional Constraints:</label>
                      <textarea
                        placeholder="Provide any additional context or information..."
                        value={additionalInfo}
                        onChange={(e) => setAdditionalInfo(e.target.value)}
                        rows={2}
                      />
                    </div>
                  </>
                ) : (
                  <p className="no-ambiguities-msg">
                    No ambiguities to resolve yet. Submit a question first!
                  </p>
                )}
              </div>
              <div className="actions">
                <button
                  className="submit-btn"
                  onClick={handleClarifySumbit}
                  disabled={!sessionId || ambiguities.length === 0}
                >
                  Submit
                </button>
              </div>
            </>
          )}
        </div>
        {/* 3. SQL Answer and Comparison Card*/}
        <div className="card output-card">
          {isTranslatingSQL ? (
            <div className="loading-overlay">
              <div className="loading-content">
                <div className="spinner"></div>
                <span>Waiting for SQL translation</span>
              </div>
            </div>
          ) : isSQLReady ? (
            <div className="output-card-content">
              <div className="output-container">
                <div className="output-section">
                  <h3>Text2SQL Output (Powered By XiYan-SQL)</h3>
                  <div className="sql-output">
                    <pre>{rawSQL}</pre>
                  </div>
                </div>
                <div className="output-section">
                  <h3>Text2SQL Output (Powered By XiYan-SQL with AmbiSQL)</h3>
                  <div className="sql-output">
                    <pre>{clarifiedSQL}</pre>
                  </div>
                </div>
              </div>
              <div className="actions">
                <button
                  className="compare-btn"
                  onClick={handleComparison}
                  disabled={!sessionId || rawSQL === null}
                >
                  Compare
                </button>
              </div>
            </div>
          ) : (
            <p className="no-output-msg">
              Awaiting final clarification and SQL generation...
            </p>
          )}
        </div>

        {/* 3. SQL Answer and Comparison Card*/}
        <div className="card output-card">
          {isTranslatingSQL ? (
            <div className="loading-overlay">
              <div className="loading-content">
                <div className="spinner"></div>
                <span>Waiting for SQL translation</span>
              </div>
            </div>
          ) : isSQLReady ? (
            <div className="output-card-content">
              <div className="output-container">
                <div className="output-section">
                  <h3>Text2SQL Output (Powered By XiYan-SQL)</h3>
                  <div className="sql-output">
                    <pre>{rawSQL}</pre>
                  </div>
                  {showComparison && (
                    <div className="result-output">
                      <span>Evaluation:</span>
                      <code>{"❌"}</code>
                    </div>
                  )}
                </div>
                <div className="output-section">
                  <h3>Text2SQL Output (Powered By XiYan-SQL with AmbiSQL)</h3>
                  <div className="sql-output">
                    <pre>{clarifiedSQL}</pre>
                  </div>
                  {showComparison && (
                    <div className="result-output">
                      <span>Evaluation:</span>
                      <code>{clarifiedResult !== "[[]]" ? "✅" : "❌"}</code>
                    </div>
                  )}
                  
                </div>
              </div>
              <div className="actions">
                <button
                  className="compare-btn"
                  onClick={handleComparison}
                  disabled={!sessionId || rawSQL === null}
                >
                  Compare
                </button>
              </div>
            </div>
          ) : (
            <p className="no-output-msg">
              Awaiting final clarification and SQL generation...
            </p>
          )}
        </div>
      </div>

      {/* <ExampleList></ExampleList> */}
      <div className="example-table-container">
        <h3 className="examples-title">Examples</h3>
        <div className="example-table-wrapper">
          <table className="example-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>Database Name</th>
                <th>DB Dialect</th>
              </tr>
            </thead>
            <tbody>
              {examples.map((example) => (
                <tr
                  key={example.id}
                  onClick={() => handleExampleSelect(example)}
                >
                  <td className="question-cell">{example.question}</td>
                  <td className="dbname-cell">{example.db_name}</td>
                  <td className="dialect-cell">{example.dialect}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

const styles = `
  :root {
    --font-family-sans: 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
    --font-family-mono: 'Fira Code', 'Consolas', monospace;

    --color-brand: #738FAB;          
    --color-brand-hover: #597087;   

    --color-bg: #F5F3F1;             
    --color-surface: #FCFCFC;        
    --color-border: #EAE8E5;       
    --color-text-primary: #5c544d;   
    --color-text-secondary: #8c857d;
    --color-text-on-brand: #FFFFFF;    

    --color-info-bg: #EAEFF4;       
    --color-info-text: #597087;       
    --color-success-bg: #EBF0E8;     
    --color-success-text: #586453;   
    --color-code-bg: #4a4540;        
    --color-code-text: #D4CEC7;       

    --border-radius-md: 6px;
    --border-radius-lg: 8px;
    --shadow-soft: 0 4px 12px rgba(92, 84, 77, 0.08);

    --example-table-bg: #FCFCFC;
    --example-table-header-bg: #e9ecef;
    --example-table-border: #dee2e6;
    --example-table-row-hover: #f8f9fa;
    --example-table-text: #495057;
    --example-table-font-family: 'Inter', sans-serif;
  }

  html {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
  }
  
  html, body, #root { height: 100%; margin: 0; padding: 0; }
  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: var(--font-family-sans);
    background-color: var(--color-bg);
    color: var(--color-text-primary);
    line-height: 1.5;
    font-size: 14px;
  }

  .dashboard {
    display: flex; flex-direction: column; height: 100vh;
    padding: 16px; max-width: 1800px; margin: 0 auto;
  }
  .layout-container {
    display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 40% 60%;
    min-height:70vh;
    gap: 16px; flex: 1; 
  }
  .card {
    position: relative;
    background: var(--color-surface);
    border-radius: var(--border-radius-lg);
    box-shadow: none; 
    border: 1px solid var(--color-border);
    padding: 20px;
    display: flex; flex-direction: column;
    overflow: hidden; height: 100%;
    min-width: 680px; max-width: 680px; width: 100%;
    transition: box-shadow 0.3s ease, border-color 0.3s ease;
  }
  .card:hover {
    border-color: #d8d4d0;
    box-shadow: var(--shadow-soft);
  }

  .user-input-card { grid-row: 1; grid-column: 1; }
  .interaction-card { grid-row: 2; grid-column: 1; }
  .output-card { grid-row: 1 / span 2; grid-column: 2; }

  h3 {
    color: var(--color-text-primary);
    font-size: 1.125rem; /* 18px */
    margin: 10px 0 12px 0;
    font-weight: 600;
  }
  
  .form-group { margin-bottom: 12px; }

  label {
    display: block; margin-bottom: 6px;
    font-weight: 500;
    color: var(--color-text-secondary);
    font-size: 0.875rem; /* 14px */
  }

  textarea, select, input[type="text"] {
    width: 100%; padding: 8px 12px;
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    font-size: 0.875rem;
    background-color: var(--color-surface);
    color: var(--color-text-primary);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }
  textarea::placeholder, input[type="text"]::placeholder { color: #a8a29a; }
  textarea:focus, select:focus, input[type="text"]:focus {
    outline: none;
    border-color: var(--color-brand);
    box-shadow: 0 0 0 3px rgba(115, 143, 171, 0.2);
  }
  textarea { min-height: 40px; resize: vertical; }

  .db-selector-group { display: flex; gap: 12px; margin-bottom: 12px; }
  .db-selector-group .form-group { flex: 1; margin-bottom: 0; }

  .loading-schema,
  .schema-box {
    border: none;
    background-color: transparent;
    padding: 0;
    height: 100%;
    max-height: initial; 
    overflow-y: auto; 
  }

  .schema-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--color-text-secondary);
    font-style: italic;
    font-size: 0.875rem;
    text-align: center;
  }
  .spinner {
    width: 24px; height: 24px; border: 3px solid var(--color-border);
    border-radius: 50%; border-top-color: var(--color-brand);
    animation: spin 1s ease-in-out infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .schema-container-wrapper {
    flex: 1; 
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .schema-content-box {
    flex-grow: 1; 
    min-height: 95px; 
    border: 1px dashed var(--color-border);
    border-radius: var(--border-radius-md);
    background-color: #FBFBFA;
    padding: 12px;
    display: flex; 
    flex-direction: column;
    font-size: 0.8em; 
  }

  .actions { display: flex; gap: 12px; margin-top: auto; padding-top: 16px; }
  button {
    padding: 10px 16px; border: 1px solid transparent; border-radius: var(--border-radius-md);
    cursor: pointer; font-weight: 600; font-size: 0.875rem;
    transition: all 0.2s ease; flex: 1;
  }
  .clear-btn {
    background-color: var(--color-surface);
    color: var(--color-text-secondary);
    border-color: var(--color-border);
  }
  .clear-btn:hover { background-color: var(--color-bg); }
  
  .submit-btn {
    background-color: var(--color-brand);
    color: var(--color-text-on-brand);
  }
  .submit-btn:hover { background-color: var(--color-brand-hover); }
  .submit-btn:disabled {
    background-color: #EAE8E5; color: #a8a29a;
    cursor: not-allowed; border-color: transparent;
  }

  .compare-btn {
    background-color: var(--color-brand);
    color: var(--color-text-on-brand);
  }
  .compare-btn:hover { background-color: var(--color-brand-hover); }
  .compare-btn:disabled {
    background-color: #EAE8E5; color: #a8a29a;
    cursor: not-allowed; border-color: transparent;
  }

  .clarifications { display: flex; flex-direction: column; gap: 16px; flex: 1; overflow-y: auto; }
  .clarification-item p { 
    background-color: var(--color-info-bg);
    color: var(--color-info-text);
    padding: 8px 12px; border-radius: var(--border-radius-md);
    margin-bottom: 8px; font-weight: 500; font-size: 0.875rem;
  }
  .no-ambiguities-msg, .no-output-msg {
    text-align: center; color: var(--color-text-secondary); font-style: italic; padding: 16px;
    font-size: 0.875rem; height: 100%; display: flex; align-items: center; justify-content: center;
  }

  .output-container { display: flex; flex-direction: column; gap: 20px; flex: 1; overflow-y: auto; }
  .output-section { padding: 0; border: none; background-color: transparent; }
  
  .sql-output {
    background-color: var(--color-code-bg);
    color: var(--color-code-text);
    padding: 12px; border-radius: var(--border-radius-md);
    font-family: var(--font-family-mono);
    font-size: 0.875rem; overflow-x: auto; max-height: 200px;
    margin-top: 8px; margin-bottom: 8px;
  }
  pre { white-space: pre-wrap; word-break: break-all; }
  
  .result-output {
    background-color: var(--color-success-bg);
    color: var(--color-success-text);
    padding: 8px 12px; border-radius: var(--border-radius-md);
    font-family: var(--font-family-mono); font-weight: 500; font-size: 0.875rem;
  }
  .result-output span { font-family: var(--font-family-sans); font-weight: 600; margin-right: 8px; }
  .result-output code { color: inherit; }

  // Example List Style
  .example-table-container {
    font-family: var(--example-table-font-family);
    max-width: 1200px;
    margin: 20px auto;
    padding: 12px 16px;
    background: var(--example-table-bg);
    border: 1px solid var(--example-table-border);
    border-radius: 8px;
    box-shadow: none;
    overflow: hidden;
  }
  
  .examples-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-text-primary);
    margin: 30px 0px 12px 0px;
    text-align: left;
    padding-left: 4px;
  }

  .example-table-wrapper {
    width: 100%;
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid var(--example-table-border);
  }
  
  .example-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .example-table th {
    background-color: var(--example-table-header-bg);
    color: var(--color-text-primary);
    font-weight: 600;
    text-align: left;
    padding: 10px 12px;
  }

  .example-table td {
    padding: 10px 12px;
    color: var(--example-table-text);
    border-top: 1px solid var(--example-table-border);
  }

  .example-table tr {
    transition: background-color 0.15s ease;
    cursor: pointer;
  }

  .example-table tr:hover {
    background-color: var(--example-table-row-hover);
  }

  .question-cell {
    text-align: left;
    max-width: 550px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .dbname-cell {
    width: 22%;
    font-weight: 500;
    text-align: left;
    color: #495057;
  }

  .dialect-cell {
    width: 18%;
    font-weight: 500;
    text-align: left;
    color: #6c757d;
  }

  //loading spin
  .loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(255, 255, 255, 0.9);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
  }
  
  .loading-content {
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  
  .loading-content span {
    margin-top: 12px;
    color: var(--color-text-primary);
    font-weight: 500;
  }

  @media (max-width: 1200px) {
    .layout-container { grid-template-columns: 1fr; grid-template-rows: auto auto auto; }
    .output-card { grid-row: 3; grid-column: 1; }
  }
  @media (max-width: 768px) {
    .db-selector-group { flex-direction: column; }
  }
`;
const App = () => (
  <>
    <style>{styles}</style>
    <SQLAmbiguityResolver />
  </>
);

export default App;
