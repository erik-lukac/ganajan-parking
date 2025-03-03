// services/parkingService.js


class ParkingService {
  // Fetch parking data with pagination and search
  async getParkingData(
    page,
    pageSize = 10,
    searchTerm = "",
    startDate,
    endDate,
    licensePrefix = "",
    categoryFilter = "",
    colorFilter = "",
    gateFilter = ""
  ) {
    try {
      const queryParams = new URLSearchParams({
        page: page,
        page_size: pageSize,
        ...(searchTerm && { search: searchTerm }),
        ...(startDate && { start_date: startDate }),
        ...(endDate && { end_date: endDate }),
        ...(licensePrefix && { license_prefix: licensePrefix }),
        ...(categoryFilter && { category: categoryFilter }),
        ...(colorFilter && { color: colorFilter }),
        ...(gateFilter && { gate: gateFilter }),
      });

      const response = await fetch(`/api/data1?${queryParams}`);
      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error("Error fetching parking data:", error);
      throw error;
    }
  }



  async getParkingDataDashboard(
    page,
    pageSize = 10,
    searchTerm = "",
  ) {
    try {
      const queryParams = new URLSearchParams({
        page: page,
        page_size: pageSize,
        ...(searchTerm && { search: searchTerm }),
      });

      const response = await fetch(`/api/dashboard/data?${queryParams}`);
      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error("Error fetching parking data:", error);
      throw error;
    }
  }

  // Get specific parking record by ID
  async getParkingRecordById(id) {
    try {
      const response = await fetch(`/api/data/${id}`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error fetching parking record:", error);
      throw error;
    }
  }

  // Get parking statistics
  async getParkingStats() {
    try {
      const response = await fetch(`/api/stats`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Error fetching parking stats:", error);
      throw error;
    }
  }

  async getTodayCount() {
    try {
      const response = await fetch(`${BASE_URL}/stats/today`);
      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error("Error fetching today count:", error);
      throw error;
    }
  }

  async getRecentEntries() {
    try {
      const response = await fetch(`${BASE_URL}/stats/recent-entries`);
      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error("Error fetching recent entries:", error);
      throw error;
    }
  }

  async getRecentExits() {
    try {
      const response = await fetch(`${BASE_URL}/stats/recent-exits`);
      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error("Error fetching recent exits:", error);
      throw error;
    }
  }

  async getCategories() {
    const response = await fetch(`/api/filters/categories`);
    const result = await response.json();
    return result.categories;
  }

  async getColors() {
    const response = await fetch(`/api/filters/colors`);
    const result = await response.json();
    return result.colors;
  }

  async getGates() {
    const response = await fetch(`/api/filters/gates`);
    const result = await response.json();
    return result.gates;
  }

  async getTodayEntries() {
    try {
      const response = await fetch(`/api/stats/today-entries`);
      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error("Error fetching today's entries:", error);
      throw error;
    }
  }

  async getTodayExits() {
    try {
      const response = await fetch(`/api/stats/today-exits`);
      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error("Error fetching today's exits:", error);
      throw error;
    }
  }

  async getTrends() {
    try {
      const response = await fetch(`/api/stats/trends`);
      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error("Error fetching trends:", error);
      throw error;
    }
  }
}

export const parkingService = new ParkingService();
