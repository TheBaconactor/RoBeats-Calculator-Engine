-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:50 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Local.GameJoinProtocol)
local v_u_3 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
require(game.ReplicatedStorage.Shared.TextSizeCache)
local v_u_5 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v7 = {}
local v_u_8 = {
    ["NoPlayer"] = 1,
    ["PlayerNotReady"] = 2,
    ["PlayerReady"] = 3
}
local v_u_9 = {
    ["Hidden"] = 1,
    ["HiddenToShowing"] = 2,
    ["Showing"] = 3,
    ["ShowingToHidden"] = 4
}
v7.new = function(_, p_u_10, p_u_11, p_u_12, p_u_13) --[[ Name: new ]] --[[ Line: 33 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_9, (copy 3): v_u_1, (copy 4): v_u_3, (copy 5): v_u_4, (copy 6): v_u_6, (copy 7): v_u_5, (copy 8): v_u_2 ]]
    local v14 = {}
    local v_u_15 = -1
    local v_u_16 = nil
    local v_u_17 = nil
    local v_u_18 = nil
    local v_u_19 = nil
    local v_u_20 = nil
    local v_u_21 = nil
    local v_u_22 = nil
    local v_u_23 = nil
    local v_u_24 = nil
    local v_u_25 = nil
    local v_u_26 = nil
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = 0
    local l_NoPlayer_0 = v_u_8.NoPlayer
    local l_Hidden_0 = v_u_9.Hidden
    local v_u_31 = 0
    local v_u_32 = false
    local v_u_33 = 0
    local function _(p34) --[[ Name: named_list ]] --[[ Line: 60 ]]
        local v35 = {}
        for v36 = 1, #p34 do
            v35[v36] = {
                ["Obj"] = p34[v36],
                ["Name"] = p34[v36].Name
            }
        end;
        return v35;
    end;
    v14.cons = function(p37) --[[ Name: cons ]] --[[ Line: 68 ]]
        --[[ Upvalues: (ref 1): v_u_32, (ref 2): v_u_28, (copy 3): p_u_12, (ref 4): v_u_29, (copy 5): p_u_10, (ref 6): v_u_16, (ref 7): v_u_17, (ref 8): v_u_18, (ref 9): v_u_19, (ref 10): v_u_20, (ref 11): v_u_21, (ref 12): v_u_22, (ref 13): v_u_23, (ref 14): v_u_24, (ref 15): v_u_25, (ref 16): v_u_26, (ref 17): v_u_27, (ref 18): v_u_1 ]]
        v_u_32 = false
        v_u_28 = p_u_12.SurfaceGui.Frame.StatusIcon
        v_u_29 = p_u_12.SurfaceGui.Frame.StatusDisplay
        local l_Frame_0 = p_u_10.SurfaceGui.Frame
        v_u_16 = l_Frame_0.DifficultyFrame.DifficultyDisplay
        v_u_17 = l_Frame_0.IconBack.Icon
        v_u_18 = l_Frame_0.SelectedElement.AlbumArt
        v_u_19 = l_Frame_0.SelectedElement.AlbumArt.AlbumArtOverlay
        v_u_20 = l_Frame_0.SelectedElement.ColorSection.PrimaryColorIcon
        v_u_21 = l_Frame_0.SelectedElement.ColorSection.SecondaryColorIcon
        v_u_22 = l_Frame_0.NameDisplay
        v_u_23 = l_Frame_0.TitleDisplay
        v_u_24 = l_Frame_0.PlayerFeverIconDisplay
        v_u_25 = l_Frame_0.GearPowerSection
        v_u_26 = v_u_25.GearPowerDisplay
        v_u_27 = l_Frame_0.ModeDisplay
        v_u_27.Image = v_u_1:transparent_assetid()
        p37:set_alpha(0)
        p37:set_scale(1)
        p37:update_status_icon_mode()
    end;
    v14.set_player_data = function(p38, p39) --[[ Name: set_player_data ]] --[[ Line: 96 ]]
        --[[ Upvalues: (ref 1): v_u_32, (ref 2): v_u_33, (ref 3): l_Hidden_0, (ref 4): v_u_9, (ref 5): v_u_31, (ref 6): l_NoPlayer_0, (ref 7): v_u_8, (ref 8): v_u_16, (ref 9): v_u_3, (ref 10): v_u_17, (ref 11): v_u_1, (ref 12): v_u_18, (ref 13): v_u_19, (ref 14): v_u_4, (ref 15): v_u_20, (ref 16): v_u_21, (ref 17): v_u_22, (ref 18): v_u_23, (ref 19): v_u_24, (ref 20): v_u_6 ]]
        if p39 == nil then
            v_u_32 = false
            v_u_33 = 0
            if l_Hidden_0 == v_u_9.Showing or l_Hidden_0 == v_u_9.HiddenToShowing then
                l_Hidden_0 = v_u_9.ShowingToHidden
                v_u_31 = 0
            end;
            l_NoPlayer_0 = v_u_8.NoPlayer
            p38:update_status_icon_mode()
        else
            if v_u_33 == p39._id then
                if l_Hidden_0 == v_u_9.Hidden or l_Hidden_0 == v_u_9.ShowingToHidden then
                    l_Hidden_0 = v_u_9.HiddenToShowing
                    v_u_31 = 0
                end;
            elseif l_Hidden_0 == v_u_9.Showing or l_Hidden_0 == v_u_9.HiddenToShowing then
                l_Hidden_0 = v_u_9.ShowingToHidden
                v_u_31 = 0
            end;
            local l__requested_song_key_0 = p39._requested_song_key
            v_u_16.Text = tostring(v_u_3:singleton():get_difficulty_for_key(l__requested_song_key_0))
            v_u_16.TextColor3 = v_u_3:singleton():get_difficulty_color_for_key(l__requested_song_key_0)
            if v_u_33 ~= p39._id then
                v_u_17.Image = v_u_1:transparent_assetid()
                v_u_1:get_user_thumbnail(p39._id, function(p40) --[[ Line: 128 ]]
                    --[[ Upvalues: (ref 1): v_u_17 ]]
                    v_u_17.Image = p40
                end)
            end;
            v_u_3:singleton():render_coverimage_for_key(v_u_18, v_u_19, l__requested_song_key_0)
            v_u_4:render_songkey_color_icons(l__requested_song_key_0, v_u_20, v_u_21)
            v_u_22.Text = p39._name
            v_u_23.Text = p39._title
            v_u_24.Image = p39._icon
            local v41 = v_u_6:singleton():get_title_for_id(p39._title_id)
            v_u_22.TextColor3 = v41:get_color()
            v_u_23.TextColor3 = v41:get_color()
            if p39._ready == true then
                l_NoPlayer_0 = v_u_8.PlayerReady
            else
                l_NoPlayer_0 = v_u_8.PlayerNotReady
            end;
            p38:update_status_icon_mode()
            v_u_33 = p39._id
            v_u_32 = true
        end;
    end;
    v14.set_matchmaking_gameinstance_player_info = function(_, p42, p43) --[[ Name: set_matchmaking_gameinstance_player_info ]] --[[ Line: 153 ]]
        --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_26, (ref 3): v_u_27, (ref 4): v_u_1, (ref 5): v_u_5 ]]
        if p42 == nil or p43 == nil then
            v_u_25.Visible = false
            v_u_26.Text = ""
            v_u_27.Image = v_u_1:transparent_assetid()
        else
            v_u_26.Text = string.format("%d", (math.floor((tonumber(p43.GearPower)))))
            local v44
            if p42._id == v_u_1:get_local_userid() then
                v44 = v_u_5:get_selected_mode()
            else
                v44 = p43.MatchMode
            end;
            v_u_27.Image = v_u_5:get_icon_for_mode(v44)
            v_u_25.Visible = v_u_5:get_selected_mode() == v_u_5.Compete
        end;
    end;
    v14.update_status_icon_mode = function(_) --[[ Name: update_status_icon_mode ]] --[[ Line: 172 ]]
        --[[ Upvalues: (ref 1): l_NoPlayer_0, (ref 2): v_u_8, (ref 3): v_u_28, (ref 4): v_u_1, (ref 5): v_u_29 ]]
        if l_NoPlayer_0 == v_u_8.NoPlayer then
            v_u_28.Image = v_u_1:get_spinner_assetid()
            v_u_29.Text = "Searching..."
            return;
        elseif l_NoPlayer_0 == v_u_8.PlayerNotReady then
            v_u_28.Image = v_u_1:get_spinner_assetid()
            v_u_29.Text = "Waiting..."
        elseif l_NoPlayer_0 == v_u_8.PlayerReady then
            v_u_28.Image = v_u_1:get_miniqueue_ready_assetid()
            v_u_29.Text = "Ready!"
        end;
    end;
    v14.behaviour_update = function(p45, p46, _) --[[ Name: behaviour_update ]] --[[ Line: 185 ]]
        --[[ Upvalues: (ref 1): l_NoPlayer_0, (ref 2): v_u_8, (ref 3): v_u_30, (ref 4): v_u_2, (ref 5): v_u_28, (ref 6): l_Hidden_0, (ref 7): v_u_9, (ref 8): v_u_32, (ref 9): v_u_31 ]]
        if l_NoPlayer_0 == v_u_8.PlayerReady then
            v_u_30 = 0
        else
            v_u_30 = v_u_2:IncrementWrap(v_u_30, -0.75 * p46, 360)
        end;
        v_u_28.Rotation = v_u_30
        if l_Hidden_0 == v_u_9.Hidden then
            p45:set_alpha(0)
            p45:set_scale(1.25)
            if v_u_32 == true then
                v_u_31 = 0
                l_Hidden_0 = v_u_9.HiddenToShowing
                return;
            end;
        elseif l_Hidden_0 == v_u_9.HiddenToShowing then
            local l_Y_0 = v_u_2:BezierPt2ForT(0, 0, 1, 0, 0, 1, 1, 1, v_u_31).Y
            p45:set_alpha(v_u_2:YForPointOf2PtLine(Vector2.new(0, 0), Vector2.new(1, 1), l_Y_0))
            p45:set_scale(v_u_2:YForPointOf2PtLine(Vector2.new(0, 1.25), Vector2.new(1, 1), l_Y_0))
            v_u_31 = v_u_31 + v_u_2:sec_to_tick(0.25) * p46
            if v_u_31 >= 1 then
                l_Hidden_0 = v_u_9.Showing
                return;
            end;
        else
            if l_Hidden_0 == v_u_9.Showing then
                p45:set_alpha(1)
                p45:set_scale(1)
                return;
            end;
            if l_Hidden_0 == v_u_9.ShowingToHidden then
                local l_Y_1 = v_u_2:BezierPt2ForT(0, 0, 1, 0, 0, 1, 1, 1, v_u_31).Y
                p45:set_alpha(v_u_2:YForPointOf2PtLine(Vector2.new(0, 1), Vector2.new(1, 0), l_Y_1))
                p45:set_scale(v_u_2:YForPointOf2PtLine(Vector2.new(0, 1), Vector2.new(1, 1.25), l_Y_1))
                v_u_31 = v_u_31 + v_u_2:sec_to_tick(0.25) * p46
                if v_u_31 >= 1 then
                    l_Hidden_0 = v_u_9.Hidden
                end;
            end;
        end;
    end;
    v14.layout = function(_) --[[ Name: layout ]] --[[ Line: 226 ]]
        --[[ Upvalues: (copy 1): p_u_11, (copy 2): p_u_13 ]]
        p_u_11:layout()
        p_u_13:layout()
    end;
    v14.set_scale = function(_, p47) --[[ Name: set_scale ]] --[[ Line: 231 ]]
        --[[ Upvalues: (copy 1): p_u_11 ]]
        p_u_11:set_scale(p47)
    end;
    v14.set_alpha = function(_, p48) --[[ Name: set_alpha ]] --[[ Line: 235 ]]
        --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_1, (copy 3): p_u_10 ]]
        if v_u_15 ~= p48 then
            v_u_15 = p48
            v_u_1:obj_set_alpha(p_u_10, v_u_15, 1)
        end;
    end;
    v14:cons()
    return v14;
end;
return v7;
