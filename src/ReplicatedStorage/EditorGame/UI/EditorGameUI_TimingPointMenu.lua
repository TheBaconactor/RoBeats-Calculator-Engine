-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:11 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
require(game.ReplicatedStorage.Shared.WaitForFinish)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Lobby.UI.UIToggleGroup)
local v_u_5 = require(game.ReplicatedStorage.Shared.AssertType)
local v6 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_7 = nil
local v_u_8 = nil
local v_u_9 = nil
v6:require_client(function() --[[ Line: 25 ]]
    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_9 ]]
    v_u_7 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_8 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_9 = require(game.ReplicatedStorage.Lobby.Menus.ValueInputUI)
end)
local v_u_16 = {
    ["remove_timing_point_at_index"] = function(_, p10, p_u_11, p_u_12, p_u_13) --[[ Name: remove_timing_point_at_index ]] --[[ Line: 251 ]]
        --[[ Upvalues: (copy 1): v_u_3, (ref 2): v_u_8, (copy 3): v_u_1, (copy 4): v_u_4 ]]
        if p_u_12 <= 0 then
            return v_u_3:warnf("Timing point index[%d] out of range", p_u_12);
        end;
        local v_u_14 = p_u_11:get_time_bar_render():get_timing_points()
        if v_u_14:count() < p_u_12 then
            return v_u_3:warnf("Timing point index[%d] out of range timing_points(%d)", p_u_12, v_u_14:count());
        end;
        if v_u_14:count() <= 1 then
            return p10._menus:push_menu(v_u_8:new(p10, p10._spui, p10._menus):set_text("Error", "Must have at least one timing point."));
        end;
        local v15 = v_u_14:get(p_u_12)
        p10._menus:push_menu(v_u_8:new(p10, p10._spui, p10._menus):set_text("Confirm", string.format("Are you sure you want to remove this timing point?\n[%d] %s - %s bpm (%sms)", p_u_12, v_u_1:format_ms_time_hundredth(v15:get_time_ms()), v_u_4.TimingPoint:timing_point_get_display_bpm(v15), v15:get_beat_length_ms())):set_okay_button_fn(function() --[[ Line: 271 ]]
            --[[ Upvalues: (copy 1): v_u_14, (copy 2): p_u_12, (copy 3): p_u_11, (copy 4): p_u_13 ]]
            v_u_14:remove_at(p_u_12)
            p_u_11:full_refresh_active_display_notes()
            if p_u_13 then
                p_u_13()
            end;
        end))
    end
}
local function _(p17) --[[ Name: resort_timing_points ]] --[[ Line: 33 ]]
    p17:sort(function(p18, p19) --[[ Line: 34 ]]
        return p18:get_time_ms() < p19:get_time_ms();
    end)
end;
v_u_16.show_menu = function(_, p_u_20, p_u_21) --[[ Name: show_menu ]] --[[ Line: 39 ]]
    --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_16, (copy 5): v_u_2, (copy 6): v_u_3 ]]
    p_u_20._menus:push_menu(v_u_7:new(p_u_20, p_u_20._spui, p_u_20._menus, function(p22) --[[ Line: 46 ]]
        --[[ Upvalues: (copy 1): p_u_21 ]]
        p22:set_header_text("Timing Points")
        p22:get_element_list():push_back("Create New Timing Point")
        for _, v23 in p_u_21:get_time_bar_render():get_timing_points():key_itr() do
            p22:get_element_list():push_back(v23)
        end;
    end, function(p24, p25, p26, _, p27) --[[ Line: 53 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_21, (ref 3): v_u_4 ]]
        if p24 == "Create New Timing Point" then
            p25.Text = "Add Timing Point"
            p26.Image = v_u_1:get_double_arrow_icon_assetid()
            p27:set_select_button_enabled(true)
            p27:set_select_button_text("Create")
            p27:get_description_display().Text = "Create a new timing point."
        else
            p25.Text = string.format("[%d] %s", p_u_21:get_time_bar_render():get_timing_points():find(p24), v_u_1:format_ms_time_hundredth(p24:get_time_ms()))
            if p_u_21:get_time_bar_render():calculate_active_timing_point() == p24 then
                p25.Text = p25.Text .. " (Active)"
            end;
            p26.Image = v_u_1:important_assetid()
            p27:get_description_display().Text = string.format("%s bpm (%sms)", v_u_4.TimingPoint:timing_point_get_display_bpm(p24), p24:get_beat_length_ms())
            p27:set_select_button_enabled(true)
            p27:set_select_button_text("Edit")
        end;
    end, function(p28) --[[ Line: 85 ]]
        --[[ Upvalues: (ref 1): v_u_16, (copy 2): p_u_20, (copy 3): p_u_21, (ref 4): v_u_2, (ref 5): v_u_3 ]]
        if p28 == nil then
            return;
        elseif p28 == "Create New Timing Point" then
            v_u_16:create_new_timing_point(p_u_20, p_u_21)
        else
            local v29 = p_u_21:get_time_bar_render():get_timing_points():find(p28)
            if v29 == v_u_2:list_end() then
                return v_u_3:warnf("Timing point not found");
            end;
            v_u_16:edit_timing_point_at_index(p_u_20, p_u_21, v29)
        end;
    end, function(p30) --[[ Line: 95 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_21 ]]
        p30:set_sub_text(string.format("Current Time: %s", v_u_1:format_ms_time_hundredth(p_u_21:get_display_time_ms())))
    end)):set_close_on_element_select(false):set_refresh_on_refocus(true)
end;
local function f_select_time_ms(p31, p32, p33, p_u_34) --[[ Name: select_time_ms ]] --[[ Line: 108 ]]
    --[[ Upvalues: (ref 1): v_u_9, (copy 2): v_u_5, (copy 3): v_u_1 ]]
    p31._menus:push_menu(v_u_9:new(p31, p31._spui, p31._menus, p33, function(p35) --[[ Line: 114 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_34 ]]
        v_u_5:is_true(p35 >= 0)
        p_u_34(p35)
    end):set_value_increment(10):set_reset_value(p33):set_range_min_max(p32:get_audio_duration_ms() * -0.25, p32:get_audio_duration_ms()):set_title_sub_text("Select Time", "This timing point will start at..."):set_value_display_info_fn(function(p36) --[[ Line: 125 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        return v_u_1:format_ms_time_hundredth(p36), "";
    end))
end;
local function f_select_beat_length(p37, p38, p39, p_u_40) --[[ Name: select_beat_length ]] --[[ Line: 130 ]]
    --[[ Upvalues: (copy 1): v_u_4, (ref 2): v_u_9, (copy 3): v_u_5, (copy 4): v_u_1 ]]
    local v_u_41 = nil
    local function _() --[[ Name: update_value_increment ]] --[[ Line: 132 ]]
        --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_4 ]]
        if v_u_41 ~= nil then
            local v42 = v_u_41:get_value()
            v_u_41:set_value_increment(v_u_4.TimingPoint:bpm_get_beat_length_ms(v_u_4.TimingPoint:beat_length_ms_get_bpm(v42) + 0.1) - v42)
        end;
    end;
    v_u_41 = p37._menus:push_menu(v_u_9:new(p37, p37._spui, p37._menus, p39, function(p43) --[[ Line: 148 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_40 ]]
        v_u_5:is_true(p43 > 0)
        p_u_40(p43)
    end, {
        ["AllowDecimals"] = true
    }):set_value_increment(-1):set_reset_value(p39):set_range_min_max(1, (math.floor(p38:get_audio_duration_ms() * 0.25))):set_title_sub_text("Select Beat Length (ms)", "This timing point will have a beat length (in milliseconds) of..."):set_value_display_info_fn(function(p44) --[[ Line: 162 ]]
        --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_4 ]]
        if v_u_41 ~= nil then
            local v45 = v_u_41:get_value()
            v_u_41:set_value_increment(v_u_4.TimingPoint:bpm_get_beat_length_ms(v_u_4.TimingPoint:beat_length_ms_get_bpm(v45) + 0.1) - v45)
        end;
        return v_u_4.TimingPoint:beat_length_ms_get_display_bgm(p44), "bpm";
    end):set_fn_on_increment(function(p46) --[[ Line: 166 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        return v_u_1:round_to_decimal_places(p46, 2);
    end))
    if v_u_41 ~= nil then
        local v47 = v_u_41:get_value()
        v_u_41:set_value_increment(v_u_4.TimingPoint:bpm_get_beat_length_ms(v_u_4.TimingPoint:beat_length_ms_get_bpm(v47) + 0.1) - v47)
    end;
end;
v_u_16.edit_timing_point_at_index = function(_, p_u_48, p_u_49, p_u_50) --[[ Name: edit_timing_point_at_index ]] --[[ Line: 172 ]]
    --[[ Upvalues: (copy 1): v_u_3, (ref 2): v_u_7, (copy 3): v_u_1, (copy 4): v_u_4, (copy 5): f_select_time_ms, (copy 6): f_select_beat_length, (copy 7): v_u_16 ]]
    if p_u_50 <= 0 then
        return v_u_3:warnf("Timing point index[%d] out of range", p_u_50);
    end;
    local v_u_51 = p_u_49:get_time_bar_render():get_timing_points()
    if v_u_51:count() < p_u_50 then
        return v_u_3:warnf("Timing point index[%d] out of range timing_points(%d)", p_u_50, v_u_51:count());
    end;
    local v_u_52 = v_u_51:get(p_u_50)
    local v_u_53 = nil
    v_u_53 = p_u_48._menus:push_menu(v_u_7:new(p_u_48, p_u_48._spui, p_u_48._menus, function(p54) --[[ Line: 188 ]]
        --[[ Upvalues: (copy 1): v_u_51, (copy 2): v_u_52 ]]
        p54:set_header_text(string.format("Timing Point [%d]", (v_u_51:find(v_u_52))))
        p54:get_element_list():push_back("Edit Time")
        p54:get_element_list():push_back("Edit Beat Length")
        p54:get_element_list():push_back("Remove Timing Point")
    end, function(p55, p56, p57, _, p58) --[[ Line: 195 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_52, (ref 3): v_u_4, (copy 4): v_u_51 ]]
        if p55 == "Edit Time" then
            p56.Text = "Edit Time"
            p57.Image = v_u_1:get_double_arrow_icon_assetid()
            p58:set_select_button_enabled(true)
            p58:set_select_button_text("Edit")
            p58:get_description_display().Text = string.format("Current Time: %s", v_u_1:format_ms_time_hundredth(v_u_52:get_time_ms()))
            return;
        elseif p55 == "Edit Beat Length" then
            p56.Text = "Edit Beat Length"
            p57.Image = v_u_1:get_double_arrow_icon_assetid()
            p58:set_select_button_enabled(true)
            p58:set_select_button_text("Edit")
            p58:get_description_display().Text = string.format("Current Beat Length: %s bpm (%sms)", v_u_4.TimingPoint:timing_point_get_display_bpm(v_u_52), v_u_52:get_beat_length_ms())
        elseif p55 == "Remove Timing Point" then
            p56.Text = "Remove Timing Point"
            p57.Image = v_u_1:important_assetid()
            p58:set_select_button_enabled(v_u_51:count() > 1)
            p58:set_select_button_text("Remove")
            p58:get_description_display().Text = "Remove this timing point."
        end;
    end, function(p59) --[[ Line: 225 ]]
        --[[ Upvalues: (ref 1): f_select_time_ms, (copy 2): p_u_48, (copy 3): p_u_49, (copy 4): v_u_52, (copy 5): v_u_51, (ref 6): f_select_beat_length, (ref 7): v_u_16, (copy 8): p_u_50, (ref 9): v_u_53 ]]
        if p59 == nil then
            return;
        elseif p59 == "Edit Time" then
            f_select_time_ms(p_u_48, p_u_49, v_u_52:get_time_ms(), function(p60) --[[ Line: 228 ]]
                --[[ Upvalues: (ref 1): v_u_52, (ref 2): v_u_51, (ref 3): p_u_49 ]]
                v_u_52:set_time_ms((math.floor(p60)))
                v_u_51:sort(function(p61, p62) --[[ Line: 34 ]]
                    return p61:get_time_ms() < p62:get_time_ms();
                end)
                p_u_49:full_refresh_active_display_notes()
            end)
            return;
        elseif p59 == "Edit Beat Length" then
            f_select_beat_length(p_u_48, p_u_49, v_u_52:get_beat_length_ms(), function(p63) --[[ Line: 235 ]]
                --[[ Upvalues: (ref 1): v_u_52, (ref 2): p_u_49 ]]
                v_u_52:set_beat_length_ms(p63)
                p_u_49:full_refresh_active_display_notes()
            end)
        elseif p59 == "Remove Timing Point" then
            v_u_16:remove_timing_point_at_index(p_u_48, p_u_49, p_u_50, function() --[[ Line: 241 ]]
                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_53 ]]
                p_u_48._menus:remove_menu(v_u_53)
            end)
        end;
    end)):set_close_on_element_select(false):set_refresh_on_refocus(true)
end;
v_u_16.create_new_timing_point = function(_, p_u_64, p_u_65) --[[ Name: create_new_timing_point ]] --[[ Line: 281 ]]
    --[[ Upvalues: (copy 1): f_select_time_ms, (copy 2): f_select_beat_length, (copy 3): v_u_4 ]]
    local v_u_66 = p_u_65:get_time_bar_render():calculate_active_timing_point()
    f_select_time_ms(p_u_64, p_u_65, math.floor((p_u_65:get_display_time_ms())), function(p_u_67) --[[ Line: 283 ]]
        --[[ Upvalues: (ref 1): f_select_beat_length, (copy 2): p_u_64, (copy 3): p_u_65, (copy 4): v_u_66, (ref 5): v_u_4 ]]
        f_select_beat_length(p_u_64, p_u_65, v_u_66:get_beat_length_ms(), function(p68) --[[ Line: 284 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_67, (ref 3): p_u_65 ]]
            local v69 = v_u_4.TimingPoint:new()
            v69:set_time_ms((math.floor(p_u_67)))
            v69:set_beat_length_ms((math.floor(p68)))
            local v70 = p_u_65:get_time_bar_render():get_timing_points()
            v70:push_back(v69)
            v70:sort(function(p71, p72) --[[ Line: 34 ]]
                return p71:get_time_ms() < p72:get_time_ms();
            end)
            p_u_65:full_refresh_active_display_notes()
        end)
    end)
end;
return v_u_16;
