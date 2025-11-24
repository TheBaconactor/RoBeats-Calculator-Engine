-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:50 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v_u_8 = {
    ["Mode"] = {
        ["Hidden"] = 0,
        ["TransitionInDelay"] = 1,
        ["TransitionIn"] = 2,
        ["Visible"] = 3
    }
}
v_u_8.new = function(_, p_u_9, p_u_10, p_u_11) --[[ Name: new ]] --[[ Line: 24 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_8, (copy 3): v_u_2, (copy 4): v_u_1, (copy 5): v_u_7, (copy 6): v_u_6, (copy 7): v_u_4, (copy 8): v_u_5 ]]
    local v12 = {}
    Vector3.new()
    Vector3.new()
    p_u_9.Parent = p_u_11.Parent
    local v_u_13 = v_u_3:new(p_u_10, p_u_11, p_u_9)
    local l_Hidden_0 = v_u_8.Mode.Hidden
    local v_u_14 = 0
    local v_u_15 = 1
    local v_u_16 = 0
    local v_u_17 = 0
    local v_u_18 = false
    v12.cons = function(p19) --[[ Name: cons ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): v_u_13 ]]
        p19:set_alpha(1)
        v_u_13:layout()
    end;
    v12.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 51 ]]
        --[[ Upvalues: (ref 1): p_u_9, (ref 2): p_u_10, (ref 3): p_u_11, (ref 4): v_u_13 ]]
        p_u_9:Destroy()
        p_u_9 = nil
        p_u_10 = nil
        p_u_11 = nil
        v_u_13 = nil
    end;
    v12.show_in = function(_, p20) --[[ Name: show_in ]] --[[ Line: 59 ]]
        --[[ Upvalues: (ref 1): l_Hidden_0, (ref 2): v_u_8, (ref 3): v_u_17, (ref 4): v_u_13 ]]
        l_Hidden_0 = v_u_8.Mode.TransitionInDelay
        v_u_17 = p20
        v_u_13:set_rotation(120)
    end;
    v12.visual_update = function(_, p21, _) --[[ Name: visual_update ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): l_Hidden_0, (ref 2): v_u_8, (ref 3): v_u_17, (ref 4): v_u_14, (ref 5): v_u_2, (ref 6): v_u_1, (ref 7): v_u_13, (ref 8): v_u_18, (ref 9): v_u_15 ]]
        if l_Hidden_0 == v_u_8.Mode.TransitionInDelay then
            v_u_17 = v_u_17 - p21
            if v_u_17 <= 0 then
                l_Hidden_0 = v_u_8.Mode.TransitionIn
            end;
        elseif l_Hidden_0 == v_u_8.Mode.TransitionIn then
            v_u_14 = v_u_14 + v_u_2:sec_to_tick(0.35) * p21
            v_u_14 = v_u_1:clamp(v_u_14, 0, 1)
            v_u_13:set_rotation_x(v_u_2:YForPointOf2PtLine(Vector2.new(0, 120), Vector2.new(1, 0), v_u_2:BezierPt2ForT(0, 0, 1, 0, 0, 1, 1, 1, v_u_14).Y))
            if v_u_14 >= 1 then
                l_Hidden_0 = v_u_8.Mode.Visible
                v_u_14 = 0
            end;
        elseif l_Hidden_0 == v_u_8.Mode.Visible and v_u_18 == true then
            v_u_14 = v_u_2:incr_wrap(v_u_14, 0.015 * p21, 6.283185307179586)
            v_u_13:set_rotation_z(math.sin(v_u_14) * 0.5)
        end;
        v_u_13:set_scale(v_u_15)
        v_u_13:layout()
    end;
    v12.set_alpha = function(_, p22) --[[ Name: set_alpha ]] --[[ Line: 97 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        v_u_16 = p22
    end;
    v12.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 100 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        return v_u_16;
    end;
    v12.set_scale = function(_, p23) --[[ Name: set_scale ]] --[[ Line: 102 ]]
        --[[ Upvalues: (ref 1): v_u_15 ]]
        v_u_15 = p23
    end;
    v12.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 103 ]]
        --[[ Upvalues: (ref 1): v_u_13 ]]
        return v_u_13:get_scale();
    end;
    v12.set_position = function(_, p24) --[[ Name: set_position ]] --[[ Line: 105 ]]
        --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_13 ]]
        p_u_9.Position = p24
        v_u_13:update_basis_offset()
    end;
    v12.set_visible = function(_, p25) --[[ Name: set_visible ]] --[[ Line: 110 ]]
        --[[ Upvalues: (ref 1): p_u_9 ]]
        p_u_9.SurfaceGui.Enabled = p25
    end;
    v12.set_player_info = function(_, p26, p27, p28, p29) --[[ Name: set_player_info ]] --[[ Line: 112 ]]
        --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_7, (ref 3): v_u_6, (ref 4): p_u_10, (ref 5): v_u_1, (ref 6): v_u_4, (ref 7): v_u_5, (ref 8): v_u_18, (ref 9): v_u_15 ]]
        local l_Frame_0 = p_u_9.SurfaceGui.Frame
        l_Frame_0.IconBack.Icon.Image = string.format("https://www.roblox.com/headshot-thumbnail/image?userId=%d&width=150&height=150&format=png", p26._id)
        l_Frame_0.NameDisplay.Text = p26._name
        local v30 = v_u_7:singleton():get_title_for_id(p26._title_id)
        if v30 then
            l_Frame_0.NameDisplay.TextColor3 = v30:get_color()
        end;
        l_Frame_0.ModeDisplay.Image = v_u_6:get_icon_for_mode(p_u_10:get_display_match_mode())
        l_Frame_0.PlayerFeverIconDisplay.Image = p26._icon
        if p_u_10:get_display_match_mode() == v_u_6.Casual then
            l_Frame_0.ScoreDisplay.Text = v_u_1:comma_value(p26._naked_score)
            l_Frame_0.GearMultDisplay.Visible = false
            l_Frame_0.GearMultText.Visible = false
        else
            l_Frame_0.ScoreDisplay.Text = v_u_1:comma_value(p26._score)
            l_Frame_0.GearMultDisplay.Visible = true
            l_Frame_0.GearMultText.Visible = true
        end;
        l_Frame_0.ScoreText.Text = "Score"
        l_Frame_0.WinnerText.Visible = p27 == 1
        l_Frame_0.RankIcon.Display.Icon.Image = v_u_4:get_rank_value_icon(p28)
        if v_u_5.GameEndDisplayRank == true then
            l_Frame_0.RankIcon.Visible = true
        else
            l_Frame_0.RankIcon.Visible = false
        end;
        if p27 == 1 then
            l_Frame_0.PlaceDisplay.Text = "1st"
        elseif p27 == 2 then
            l_Frame_0.PlaceDisplay.Text = "2nd"
        elseif p27 == 3 then
            l_Frame_0.PlaceDisplay.Text = "3rd"
        else
            l_Frame_0.PlaceDisplay.Text = "4th"
        end;
        if p26._naked_score == nil or p26._naked_score == 0 then
            l_Frame_0.GearMultDisplay.Text = "x1.0"
        else
            l_Frame_0.GearMultDisplay.Text = string.format("x%.2f", p_u_10:get_display_match_mode() == v_u_6.Casual and 1 or p26:get_gear_multiplier())
        end;
        v_u_18 = p29
        if v_u_18 == true then
            v_u_15 = 1.15
        else
            v_u_15 = 1
        end;
    end;
    v12:cons()
    return v12;
end;
return v_u_8;
