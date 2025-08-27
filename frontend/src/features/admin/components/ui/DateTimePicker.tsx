import React, { useState, useRef, useEffect } from 'react';
import { Calendar, Clock, ChevronLeft, ChevronRight } from 'lucide-react';
import { format, parse, isValid, startOfMonth, endOfMonth, startOfWeek, endOfWeek, addDays, addMonths, subMonths, isSameMonth, isSameDay, isToday } from 'date-fns';
import { vi } from 'date-fns/locale';

interface DateTimePickerProps {
  value?: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  showTime?: boolean;
  minDate?: Date;
  maxDate?: Date;
  className?: string;
  label?: string;
  error?: string;
}

export const DateTimePicker: React.FC<DateTimePickerProps> = ({
  value = '',
  onChange,
  placeholder = 'DD/MM/YYYY',
  required = false,
  disabled = false,
  showTime = false,
  minDate,
  maxDate,
  className = '',
  label,
  error
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [timeValue, setTimeValue] = useState('00:00');
  const [inputValue, setInputValue] = useState(value);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Parse initial value
  useEffect(() => {
    if (value) {
      let parsedDate: Date | null = null;
      
      // Try different date formats
      const formats = ['dd/MM/yyyy', 'yyyy-MM-dd', 'dd-MM-yyyy'];
      
      for (const fmt of formats) {
        try {
          parsedDate = parse(value.split(' ')[0], fmt, new Date());
          if (isValid(parsedDate)) break;
        } catch {
          continue;
        }
      }
      
      if (parsedDate && isValid(parsedDate)) {
        setSelectedDate(parsedDate);
        setCurrentMonth(parsedDate);
        
        if (showTime && value.includes(' ')) {
          const timePart = value.split(' ')[1];
          if (timePart && timePart.match(/^\d{2}:\d{2}/)) {
            setTimeValue(timePart.substring(0, 5));
          }
        }
        
        setInputValue(format(parsedDate, 'dd/MM/yyyy') + (showTime ? ` ${timeValue}` : ''));
      } else {
        setInputValue(value);
      }
    }
  }, [value, showTime]);

  // Close picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    
    // Try to parse the input value
    if (newValue) {
      const datePart = newValue.split(' ')[0];
      let parsedDate: Date | null = null;
      
      // Try parsing as DD/MM/YYYY
      if (datePart.match(/^\d{1,2}\/\d{1,2}\/\d{4}$/)) {
        parsedDate = parse(datePart, 'dd/MM/yyyy', new Date());
      }
      
      if (parsedDate && isValid(parsedDate)) {
        setSelectedDate(parsedDate);
        setCurrentMonth(parsedDate);
        
        if (showTime) {
          const timePart = newValue.split(' ')[1] || timeValue;
          onChange(`${format(parsedDate, 'yyyy-MM-dd')} ${timePart}`);
        } else {
          onChange(format(parsedDate, 'yyyy-MM-dd'));
        }
      } else {
        onChange(newValue);
      }
    } else {
      onChange('');
    }
  };

  const handleDateSelect = (date: Date) => {
    setSelectedDate(date);
    const formattedDate = format(date, 'dd/MM/yyyy');
    
    if (showTime) {
      setInputValue(`${formattedDate} ${timeValue}`);
      onChange(`${format(date, 'yyyy-MM-dd')} ${timeValue}`);
    } else {
      setInputValue(formattedDate);
      onChange(format(date, 'yyyy-MM-dd'));
      setIsOpen(false);
    }
  };

  const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = e.target.value;
    setTimeValue(newTime);
    
    if (selectedDate) {
      const formattedDate = format(selectedDate, 'dd/MM/yyyy');
      setInputValue(`${formattedDate} ${newTime}`);
      onChange(`${format(selectedDate, 'yyyy-MM-dd')} ${newTime}`);
    }
  };

  const isDateDisabled = (date: Date) => {
    if (minDate && date < minDate) return true;
    if (maxDate && date > maxDate) return true;
    return false;
  };

  const renderCalendar = () => {
    const monthStart = startOfMonth(currentMonth);
    const monthEnd = endOfMonth(currentMonth);
    const startDate = startOfWeek(monthStart, { weekStartsOn: 1 });
    const endDate = endOfWeek(monthEnd, { weekStartsOn: 1 });

    const days = [];
    let day = startDate;

    while (day <= endDate) {
      days.push(day);
      day = addDays(day, 1);
    }

    const weeks = [];
    for (let i = 0; i < days.length; i += 7) {
      weeks.push(days.slice(i, i + 7));
    }

    return (
      <div className="p-4">
        {/* Month navigation */}
        <div className="flex items-center justify-between mb-4">
          <button
            type="button"
            onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <ChevronLeft size={16} />
          </button>
          <h3 className="font-medium">
            {format(currentMonth, 'MMMM yyyy', { locale: vi })}
          </h3>
          <button
            type="button"
            onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <ChevronRight size={16} />
          </button>
        </div>

        {/* Day headers */}
        <div className="grid grid-cols-7 gap-1 mb-2">
          {['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'].map(day => (
            <div key={day} className="text-center text-xs font-medium text-gray-500 p-2">
              {day}
            </div>
          ))}
        </div>

        {/* Calendar days */}
        <div className="grid grid-cols-7 gap-1">
          {weeks.map((week, weekIndex) =>
            week.map((day, dayIndex) => {
              const isCurrentMonth = isSameMonth(day, currentMonth);
              const isSelected = selectedDate && isSameDay(day, selectedDate);
              const isTodayDate = isToday(day);
              const isDisabled = isDateDisabled(day);

              return (
                <button
                  key={`${weekIndex}-${dayIndex}`}
                  type="button"
                  onClick={() => !isDisabled && handleDateSelect(day)}
                  disabled={isDisabled}
                  className={`
                    p-2 text-sm rounded hover:bg-gray-100 transition-colors
                    ${!isCurrentMonth ? 'text-gray-300' : 'text-gray-900'}
                    ${isSelected ? 'bg-blue-500 text-white hover:bg-blue-600' : ''}
                    ${isTodayDate && !isSelected ? 'bg-blue-50 text-blue-600 font-medium' : ''}
                    ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                  `}
                >
                  {format(day, 'd')}
                </button>
              );
            })
          )}
        </div>

        {/* Time picker */}
        {showTime && (
          <div className="mt-4 pt-4 border-t">
            <div className="flex items-center gap-2">
              <Clock size={16} className="text-gray-500" />
              <input
                type="time"
                value={timeValue}
                onChange={handleTimeChange}
                className="px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="mt-4 pt-4 border-t flex justify-end gap-2">
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
          >
            Hủy
          </button>
          {showTime && (
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Xác nhận
            </button>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-2">
      {label && (
        <label className="block text-base-600 font-medium">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      
      <div className="relative" ref={containerRef}>
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onFocus={() => setIsOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          required={required}
          className={`
            w-full px-4 py-2 pr-10 border border-gray-300 rounded-md 
            focus:outline-none focus:ring-2 focus:ring-base-500/20 focus:border-base-500
            ${disabled ? 'bg-gray-100 cursor-not-allowed' : ''}
            ${error ? 'border-red-500' : ''}
            ${className}
          `}
        />
        
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
        >
          <Calendar size={20} />
        </button>

        {/* Dropdown calendar */}
        {isOpen && (
          <div className="absolute top-full left-0 mt-1 bg-white border border-gray-300 rounded-lg shadow-lg z-50 min-w-[300px]">
            {renderCalendar()}
          </div>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}
    </div>
  );
};

export default DateTimePicker;
