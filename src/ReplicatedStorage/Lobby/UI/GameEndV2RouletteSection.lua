-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:53 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPRange)
local v_u_6 = require(game.ReplicatedStorage.Shared.UDimObjWrapper)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.MatchEndRouletteReward)
local v8 = {}
local v_u_9 = {
    ["Waiting"] = 0,
    ["ShowDelay"] = 1,
    ["Show"] = 2,
    ["SpinAnim"] = 3,
    ["FadeInSelect"] = 5,
    ["Finished"] = 6
}
v8.new = function(_, _, _, p_u_10) --[[ Name: new ]] --[[ Line: 26 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): v_u_6, (copy 5): v_u_4, (copy 6): v_u_1, (copy 7): v_u_3, (copy 8): v_u_7 ]]
    local v11 = {}
    local l_Waiting_0 = v_u_9.Waiting
    local v_u_12 = 0
    local v_u_13 = 0
    local v_u_14 = false
    local v_u_15 = v_u_2:new()
    local v_u_16 = nil
    local v_u_17 = v_u_5:new(-100, 100)
    local v_u_18 = nil
    local v_u_19 = nil
    local v_u_20 = nil
    local v_u_21 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 40 ]]
        --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_20, (ref 3): v_u_18, (ref 4): v_u_6, (ref 5): v_u_19, (ref 6): v_u_4, (ref 7): v_u_16, (ref 8): v_u_1, (copy 9): v_u_15, (copy 10): v_u_17 ]]
        p_u_10:get_child_part().SurfaceGui.Enabled = false
        p_u_10:set_scale(0)
        local l_Frame_0 = p_u_10:get_child_part().SurfaceGui.Frame
        local l_RouletteFrame_0 = l_Frame_0.RouletteSection.RouletteFrame
        v_u_20 = l_Frame_0.RewardNameDisplay
        v_u_20.Text = ""
        v_u_18 = v_u_6:new(l_RouletteFrame_0.SelectedItemHighlight)
        v_u_19 = v_u_6:new(l_Frame_0.RouletteSection.ShineImage)
        v_u_18:set_alpha(0)
        v_u_19:set_alpha(0)
        v_u_19._rotation_t = 0
        v_u_19._start_size_x = v_u_19._sizex
        for v22 = -2, 2 do
            local v23 = l_RouletteFrame_0:FindFirstChild(string.format("Icon(%d)", v22))
            v_u_4:is_non_nil(v23)
            local v24 = v_u_6:new(v23)
            if v22 == 0 then
                v_u_16 = v24
            end;
            v24._start_x = v24._x
            v24._reward_name = ""
            v24._reward_name_color = v_u_1:color3(255, 255, 255)
            v_u_15:push_back(v24)
        end;
        v_u_17:set_min_max(v_u_15:get(1)._x, v_u_15:get(v_u_15:count())._x)
    end;
    v11.behaviour_update = function(_, p25) --[[ Name: behaviour_update ]] --[[ Line: 70 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): l_Waiting_0, (ref 3): v_u_9, (ref 4): v_u_12, (ref 5): v_u_1, (ref 6): v_u_3, (ref 7): v_u_13, (copy 8): p_u_10, (ref 9): v_u_18, (ref 10): v_u_19, (copy 11): v_u_15, (copy 12): v_u_17, (ref 13): v_u_16, (ref 14): v_u_20 ]]
        if v_u_14 ~= false then
            if l_Waiting_0 == v_u_9.ShowDelay then
                v_u_12 = v_u_1:clamp(v_u_12 + v_u_3:SecondsToTick(0.25) * p25, 0, 1)
                if v_u_12 >= 1 then
                    l_Waiting_0 = v_u_9.Show
                    v_u_12 = 0
                    v_u_13 = 0
                end;
            elseif l_Waiting_0 == v_u_9.Show then
                v_u_12 = v_u_1:clamp(v_u_12 + v_u_3:SecondsToTick(0.75) * p25, 0, 1)
                p_u_10:set_scale(v_u_3:BezierValForT(Vector2.new(0, 0), Vector2.new(0.5, 1.5), Vector2.new(0.5, 1), Vector2.new(1, 1), v_u_12).Y)
                if v_u_12 >= 1 then
                    l_Waiting_0 = v_u_9.SpinAnim
                    v_u_12 = 0
                end;
            elseif l_Waiting_0 == v_u_9.SpinAnim then
                if v_u_13 >= 1 then
                    l_Waiting_0 = v_u_9.FadeInSelect
                    v_u_12 = 0
                end;
            elseif l_Waiting_0 == v_u_9.FadeInSelect then
                v_u_12 = v_u_1:clamp(v_u_12 + v_u_3:SecondsToTick(0.5) * p25, 0, 1)
                v_u_18:set_alpha(v_u_12)
                v_u_19:set_alpha(v_u_12)
                if v_u_12 >= 1 then
                    l_Waiting_0 = v_u_9.Finished
                    v_u_12 = 0
                end;
            end;
            if l_Waiting_0 == v_u_9.Show or l_Waiting_0 == v_u_9.SpinAnim then
                v_u_13 = v_u_1:clamp(v_u_13 + v_u_3:SecondsToTick(3) * p25, 0, 1)
                local l_Y_0 = v_u_3:BezierValForT(Vector2.new(0, 0), Vector2.new(0, 2), Vector2.new(1, 10), Vector2.new(8, 10), v_u_13).Y
                local v26 = nil
                local v27 = 0
                for v28 = 1, v_u_15:count() do
                    local v29 = v_u_15:get(v28)
                    v29:set_pos(v_u_3:wrap_val(v29._start_x - l_Y_0 * (v_u_17._max - v_u_17._min), v_u_17._min, v_u_17._max), v29._y)
                    if v29._x >= v_u_16._start_x then
                        local v30 = v29._x - v_u_16._start_x
                        if v26 == nil or v30 < v27 then
                            v27 = v30
                            v26 = v29
                        end;
                    end;
                end;
                if v26 ~= nil and v26._reward_name ~= nil then
                    v_u_20.Text = v26._reward_name
                    v_u_20.TextColor3 = v26._reward_name_color
                    v_u_20.TextTransparency = v_u_1:tra(0.5)
                end;
            elseif l_Waiting_0 == v_u_9.FadeInSelect or l_Waiting_0 == v_u_9.Finished then
                v_u_20.Text = v_u_16._reward_name
                v_u_20.TextColor3 = v_u_16._reward_name_color
                v_u_20.TextTransparency = v_u_1:tra(1)
            end;
            if l_Waiting_0 == v_u_9.FadeInSelect or l_Waiting_0 == v_u_9.Finished then
                v_u_19._rotation_t = v_u_3:IncrementWrap(v_u_19._rotation_t, v_u_3:SecondsToTick(4) * p25, 6.283185307179586)
                v_u_19:set_rotation_rad(v_u_19._rotation_t)
                local v31 = v_u_19._start_size_x + math.sin(v_u_19._rotation_t * 13) * 15
                v_u_19:set_size(v31, v31)
            end;
        end;
    end;
    v11.load_reward_info = function(_, p32) --[[ Name: load_reward_info ]] --[[ Line: 144 ]]
        --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_7, (ref 3): v_u_21, (copy 4): v_u_15, (ref 5): v_u_16, (ref 6): v_u_14, (ref 7): v_u_12, (ref 8): l_Waiting_0, (ref 9): v_u_9 ]]
        if p32.RouletteTable ~= nil and p32.RouletteReward ~= nil then
            p_u_10:get_child_part().SurfaceGui.Enabled = true
            local v33 = v_u_7:reward_table_to_list(p32.RouletteTable)
            local v34 = v_u_7.RewardEntry:from_table(p32.RouletteReward)
            v_u_21 = v34
            for v35 = 1, v_u_15:count() do
                local v36 = v_u_15:get(v35)
                if v36 == v_u_16 then
                    v34:render_image(v36._obj, v36._obj.Overlay)
                    v36._reward_name = v34:get_name()
                    v36._reward_name_color = v34:get_name_color()
                else
                    local v37 = v33:random()
                    v37:render_image(v36._obj, v36._obj.Overlay)
                    v36._reward_name = v37:get_name()
                    v36._reward_name_color = v37:get_name_color()
                end;
            end;
            v_u_14 = true
            v_u_12 = 0
            l_Waiting_0 = v_u_9.ShowDelay
        end;
    end;
    v11.layout = function(_) --[[ Name: layout ]] --[[ Line: 176 ]]
        --[[ Upvalues: (copy 1): p_u_10 ]]
        p_u_10:layout()
    end;
    f_cons()
    return v11;
end;
return v8;
