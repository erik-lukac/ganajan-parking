import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { IconPlus, IconDownload, IconHistory } from '@tabler/icons-react';
import '../Styles/Export.css'; // Import custom CSS

const Export = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showFiltersModal, setShowFiltersModal] = useState(false);
  const [recordCount, setRecordCount] = useState(0);
  const [exportTab, setExportTab] = useState('Full Database');
  const [fileFormat, setFileFormat] = useState('.csv');
  const [fileName, setFileName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filterOptions, setFilterOptions] = useState({});
  const [exportLogs, setExportLogs] = useState([]);
  const [availableLicenses] = useState(["MH", "GJ", "AP", "TS", "NL", "TN", "KL", "KA"]);
  const [categories, setCategories] = useState([]);
  const [colors, setColors] = useState([]);
  const [gates, setGates] = useState([]);
  const [items, setItems] = useState([]);

  useEffect(() => {
    const authItems = JSON.parse(localStorage.getItem('auth'));
    if (authItems) {
      setItems(authItems);
    }
  }, []);

  console.log(items);

  const fetchRecordCount = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await axios.get('/api/data1', {
        params: {
          ...convertFiltersToParams(filterOptions),
          page: 1,
          page_size: 1,
          export_type: exportTab,
          search: filterOptions.search || '',
        },
      });
      setRecordCount(response.data.total_records || 0);
    } catch (error) {
      console.error('Error fetching record count:', error);
      setError('Failed to fetch record count');
      setRecordCount(0);
    } finally {
      setIsLoading(false);
    }
  };

  const convertFiltersToParams = (filters) => {
    const params = {};
    
    if (filters.startDate) {
      const start = new Date(`${filters.startDate}T00:00:00Z`);
      params.start_date = start.toUTCString(); // e.g., "Sun, 02 Mar 2025 00:00:00 GMT"
      console.log(params.start_date);
    }
    if (filters.endDate) {
      const end = new Date(`${filters.endDate}T23:59:59Z`);
      params.end_date = end.toUTCString(); // e.g., "Sun, 02 Mar 2025 23:59:59 GMT"
    }
    if (filters.categories?.length) params.categories = filters.categories.join(',');
    if (filters.colors?.length) params.colors = filters.colors.join(',');
    if (filters.gates?.length) params.gates = filters.gates.join(',');
    if (filters.licensePrefix?.length) params.license_prefix = filters.licensePrefix.join(',');
    
    return params;
  };
  useEffect(() => {
    fetchRecordCount();
    fetchExportLogs();
    fetchFilterOptions();
  }, [JSON.stringify(filterOptions), exportTab]);

  const fetchExportLogs = async () => {
    try {
      const response = await axios.get('/api/export-logs');
      setExportLogs(response.data);
    } catch (error) {
      console.error('Error fetching export logs:', error);
    }
  };

  const fetchFilterOptions = async () => {
    try {
      const [cats, cols, gts] = await Promise.all([
        axios.get('/api/filters/categories'),
        axios.get('/api/filters/colors'),
        axios.get('/api/filters/gates'),
      ]);
      setCategories(cats.data.categories || cats.data);
      setColors(cols.data.colors || cols.data);
      setGates(gts.data.gates || gts.data);
    } catch (error) {
      console.error('Error fetching filter options:', error);
    }
  };

  const handleExport = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const exportResponse = await axios.get('/api/export', {
        params: {
          ...convertFiltersToParams(filterOptions),
          file_format: fileFormat.replace('.', ''),
          export_type: exportTab,
          file_name: fileName || `export_${new Date().toISOString().replace(/[:.]/g, '-')}`,
        },
        responseType: 'blob',
      });
  
      const blob = new Blob([exportResponse.data], {
        type:
          fileFormat === '.csv'
            ? 'text/csv'
            : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
  
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${fileName || 'export'}${fileFormat}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
  
      // Log export separately
      try {
        const authData = JSON.parse(localStorage.getItem('auth'));
        const logResponse = await axios.post('/api/log-export', {
          fileName: fileName || 'export',
          format: fileFormat,
          exportType: exportTab,
          filters: filterOptions,
          recordCount,
          user: authData?.username || 'Unknown',
          timestamp: new Date().toISOString(), // Include timestamp for sorting
        });
        console.log('Log response:', logResponse.data); // Debug log response
        fetchExportLogs(); // Refresh logs after successful log entry
      } catch (logError) {
        console.error('Logging export failed:', logError);
        setError('Export succeeded, but failed to log the export.');
      }
  
      setIsModalOpen(false);
    } catch (error) {
      console.error('Export failed:', error);
      setError('Failed to export data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogDownload = async (log) => {
    try {
      const response = await axios.get(`/api/download-export/${log.id}`, {
        responseType: 'blob',
      });

      const blob = new Blob([response.data], {
        type:
          log.format === '.csv'
            ? 'text/csv'
            : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${log.fileName}${log.format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const renderExportTabs = () => {
    const tabs = ['Full Database', 'Vehicle Filters', 'Date & Time'];
    return (
      <div className="export-tabs">
        {tabs.map((tab) => (
          <button
            key={tab}
            className={`export-tab ${exportTab === tab ? 'active' : ''}`}
            onClick={() => setExportTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>
    );
  };

  const renderTabContent = () => {
    switch (exportTab) {
      case 'Full Database':
        return <div className="tab-content">Exporting entire database</div>;
      case 'Vehicle Filters':
        return (
          <div className="tab-content">
            <button
              className="select-filters-button"
              onClick={() => setShowFiltersModal(true)}
            >
              Select Filters
            </button>
            <div className="selected-filters">
              {filterOptions.licensePrefix?.length > 0 && (
                <span>Licenses ({filterOptions.licensePrefix.length})</span>
              )}
              {filterOptions.categories?.length > 0 && (
                <span>Categories ({filterOptions.categories.length})</span>
              )}
              {filterOptions.colors?.length > 0 && (
                <span>Colors ({filterOptions.colors.length})</span>
              )}
              {filterOptions.gates?.length > 0 && (
                <span>Gates ({filterOptions.gates.length})</span>
              )}
            </div>
          </div>
        );
      case 'Date & Time':
        return (
          <div className="tab-content">
            <div className="input-group">
              <label>Start Date</label>
              <input
                type="date"
                value={filterOptions.startDate || ''}
                onChange={(e) =>
                  setFilterOptions((prev) => ({ ...prev, startDate: e.target.value }))
                }
              />
            </div>
            <div className="input-group">
              <label>End Date</label>
              <input
                type="date"
                value={filterOptions.endDate || ''}
                onChange={(e) =>
                  setFilterOptions((prev) => ({ ...prev, endDate: e.target.value }))
                }
              />
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="export-page">
      <div className="header">
        <h1>Export</h1>
        <button className="new-export-button" onClick={() => setIsModalOpen(true)}>
          <IconPlus className="icon" />
          New Export
        </button>
      </div>

      <div className="export-logs">
        <div className="logs-header">
          <h2>Export History</h2>
          <IconHistory size={20} className="history-icon" />
        </div>
        <div className="logs-table">
          <table>
            <thead>
              <tr>
                <th>File Name</th>
                <th>Format</th>
                <th>Date</th>
                <th>Records</th>
                <th>Export Type</th>
                <th>User</th>
              </tr>
            </thead>
            <tbody>
              {exportLogs.map((log) => (
                <tr key={log.id}>
                  <td>{log.fileName}</td>
                  <td>{log.format}</td>
                  <td>{formatDate(log.timestamp)}</td>
                  <td>{log.recordCount.toLocaleString()}</td>
                  <td>
                    {log.exportType}
                    {log.filters && (
                      <div className="filter-details">
                        {log.exportType === 'Vehicle Filters' && (
                          <>
                            {log.filters.licensePrefix?.length > 0 && (
                              <span>
                                Licenses: {Array.isArray(log.filters.licensePrefix)
                                  ? log.filters.licensePrefix.join(', ')
                                  : log.filters.licensePrefix}
                              </span>
                            )}
                            {log.filters.categories?.length > 0 && (
                              <span>Categories: {log.filters.categories.join(', ')}</span>
                            )}
                            {log.filters.colors?.length > 0 && (
                              <span>Colors: {log.filters.colors.join(', ')}</span>
                            )}
                            {log.filters.gates?.length > 0 && (
                              <span>Gates: {log.filters.gates.join(', ')}</span>
                            )}
                          </>
                        )}
                        {log.exportType === 'Date & Time' && (
                          <span>
                            {formatDate(log.filters.startDate)} - {formatDate(log.filters.endDate)}
                          </span>
                        )}
                      </div>
                    )}
                  </td>
                  <td>{log.user || 'System'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h2>Export Options</h2>
              <button className="close-button" onClick={() => setIsModalOpen(false)}>
                ✕
              </button>
            </div>

            {renderExportTabs()}

            <div className="modal-content">
              <div className="record-count">
                <span>No. of Records: {recordCount}</span>
                {isLoading && <span className="loading">Loading...</span>}
              </div>
              {error && <div className="error">{error}</div>}
              {renderTabContent()}
            </div>

            <div className="file-options">
              <div className="file-name">
                <label>File Name</label>
                <input
                  type="text"
                  value={fileName}
                  onChange={(e) => setFileName(e.target.value)}
                />
              </div>
              <div className="file-type">
                <label>File Type</label>
                <select
                  value={fileFormat}
                  onChange={(e) => setFileFormat(e.target.value)}
                >
                  <option value=".xlsx">.xlsx</option>
                  <option value=".csv">.csv</option>
                </select>
              </div>
            </div>

            <div className="modal-footer">
              <button className="cancel-button" onClick={() => setIsModalOpen(false)}>
                Cancel
              </button>
              <button
                className="export-button"
                onClick={handleExport}
                disabled={isLoading || recordCount === 0}
              >
                {isLoading ? 'Exporting...' : (
                  <>
                    <IconDownload className="icon" />
                    Export
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {showFiltersModal && (
        <div className="filters-modal-overlay">
          <div className="filters-modal">
            <div className="filters-modal-header">
              <h2>Select Filters</h2>
              <button
                className="close-button"
                onClick={() => setShowFiltersModal(false)}
              >
                ✕
              </button>
            </div>
            <div className="filters-modal-content">
              <div className="filter-section">
                <h4>License Plate Prefix</h4>
                <div className="checkbox-group columns-2">
                  {availableLicenses.map((license) => (
                    <label key={license} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={filterOptions.licensePrefix?.includes(license) || false}
                        onChange={(e) => {
                          const updatedPrefixes = filterOptions.licensePrefix || [];
                          if (e.target.checked) {
                            setFilterOptions((prev) => ({
                              ...prev,
                              licensePrefix: [...updatedPrefixes, license],
                            }));
                          } else {
                            setFilterOptions((prev) => ({
                              ...prev,
                              licensePrefix: updatedPrefixes.filter((l) => l !== license),
                            }));
                          }
                        }}
                      />
                      <span>{license}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="filter-section">
                <h4>Category</h4>
                <div className="checkbox-group">
                  {categories.map((category) => (
                    <label key={category} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={filterOptions.categories?.includes(category) || false}
                        onChange={(e) => {
                          const updatedCategories = filterOptions.categories || [];
                          if (e.target.checked) {
                            setFilterOptions((prev) => ({
                              ...prev,
                              categories: [...updatedCategories, category],
                            }));
                          } else {
                            setFilterOptions((prev) => ({
                              ...prev,
                              categories: updatedCategories.filter((c) => c !== category),
                            }));
                          }
                        }}
                      />
                      <span>{category}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="filter-section">
                <h4>Color</h4>
                <div className="checkbox-group">
                  {colors.map((color) => (
                    <label key={color} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={filterOptions.colors?.includes(color) || false}
                        onChange={(e) => {
                          const updatedColors = filterOptions.colors || [];
                          if (e.target.checked) {
                            setFilterOptions((prev) => ({
                              ...prev,
                              colors: [...updatedColors, color],
                            }));
                          } else {
                            setFilterOptions((prev) => ({
                              ...prev,
                              colors: updatedColors.filter((c) => c !== color),
                            }));
                          }
                        }}
                      />
                      <span>{color}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="filter-section">
                <h4>Gate</h4>
                <div className="checkbox-group">
                  {gates.map((gate) => (
                    <label key={gate} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={filterOptions.gates?.includes(gate) || false}
                        onChange={(e) => {
                          const updatedGates = filterOptions.gates || [];
                          if (e.target.checked) {
                            setFilterOptions((prev) => ({
                              ...prev,
                              gates: [...updatedGates, gate],
                            }));
                          } else {
                            setFilterOptions((prev) => ({
                              ...prev,
                              gates: updatedGates.filter((g) => g !== gate),
                            }));
                          }
                        }}
                      />
                      <span>{gate}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="filters-modal-footer">
              <button
                className="cancel-button"
                onClick={() => setShowFiltersModal(false)}
              >
                Cancel
              </button>
              <button
                className="export-button"
                onClick={() => setShowFiltersModal(false)}
              >
                Apply Filters
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Export;
