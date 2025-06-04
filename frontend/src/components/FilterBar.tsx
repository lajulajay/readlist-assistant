import React, { ChangeEvent } from "react";

interface Props {
  filters: {
    genre: string;
    minRatings: string;
    minRating: string;
  };
  setFilters: (filters: Props["filters"]) => void;
}

const FilterBar: React.FC<Props> = ({ filters, setFilters }) => {
  const updateFilter = (e: ChangeEvent<HTMLInputElement>) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  };

  return (
    <div style={{ marginBottom: 20 }}>
      <label>
        Genre:&nbsp;
        <input
          name="genre"
          value={filters.genre}
          onChange={updateFilter}
          placeholder="e.g. Biography"
        />
      </label>
      &nbsp;&nbsp;
      <label>
        Min Ratings:&nbsp;
        <input
          name="minRatings"
          value={filters.minRatings}
          onChange={updateFilter}
          type="number"
          min="0"
        />
      </label>
      &nbsp;&nbsp;
      <label>
        Min Avg Rating:&nbsp;
        <input
          name="minRating"
          value={filters.minRating}
          onChange={updateFilter}
          type="number"
          min="0"
          max="5"
          step="0.1"
        />
      </label>
    </div>
  );
};

export default FilterBar;