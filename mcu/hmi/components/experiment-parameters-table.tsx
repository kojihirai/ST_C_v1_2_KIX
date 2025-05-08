"use client"

interface ExperimentParametersTableProps {
  parameters: Record<string, number | string | boolean>;
  independentVariables: Array<{
    name: string;
    value: number;
    description: string;
    units: string;
  }>;
}

export function ExperimentParametersTable({
  parameters,
  independentVariables
}: ExperimentParametersTableProps) {
  // Log for debugging
  console.log('ExperimentParametersTable - parameters:', parameters);
  console.log('ExperimentParametersTable - independent variables:', independentVariables);

  // Check if we have independent variables to display
  if (!independentVariables || independentVariables.length === 0) {
    return (
      <div className="text-sm text-gray-500">
        No independent variables defined for this project.
      </div>
    );
  }

  // Helper function to get the value with proper formatting
  const getDisplayValue = (variable: { name: string; value: number; units: string }, experimentValue: number | string | boolean | undefined) => {
    // First try to get the experiment-specific value
    if (experimentValue !== undefined && experimentValue !== null) {
      return `${experimentValue}${variable.units ? ` ${variable.units}` : ''}`;
    }
    // If no experiment value is set, show project default with indication
    return `${variable.value}${variable.units ? ` ${variable.units}` : ''} (default)`;
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Variable
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Value
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Description
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {independentVariables.map((variable) => {
            // Get experiment-specific value
            const experimentValue = parameters && parameters[variable.name];
            const displayValue = getDisplayValue(variable, experimentValue);

            return (
              <tr key={variable.name}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {variable.name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {displayValue}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {variable.description}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
} 