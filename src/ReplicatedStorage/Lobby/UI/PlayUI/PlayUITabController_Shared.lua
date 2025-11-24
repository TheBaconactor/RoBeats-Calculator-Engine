-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:56 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_5 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_10 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_11 = require(game.ReplicatedStorage.Shared.MissionInfo)
require(game.ReplicatedStorage.Shared.MissionTimeframe)
require(game.ReplicatedStorage.Shared.MissionDifficulty)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.LeaderboardSongPurchaseInfo)
local v_u_13 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_15 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_16 = require(game.ReplicatedStorage.Shared.MissionType)
local v_u_17 = require(game.ReplicatedStorage.Shared.AudioRank)
require(game.ReplicatedStorage.Shared.PlayerListActivity)
local v_u_18 = require(game.ReplicatedStorage.PlayerInfo.SaleInfo)
local v_u_19 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_20 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_21 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_22 = require(game.ReplicatedStorage.Shared.Mission.MissionActiveData)
require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_23 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v24 = require(game.ReplicatedStorage.Shared.PlayerListEntry)
local v25 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_26 = nil
local v_u_27 = nil
local v_u_28 = nil
local v_u_29 = nil
local v_u_30 = nil
local v_u_31 = nil
local v_u_32 = nil
local v_u_33 = nil
local v_u_34 = nil
local v_u_35 = nil
local v_u_36 = nil
v25:require_client(function() --[[ Line: 45 ]]
    --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_27, (ref 3): v_u_28, (ref 4): v_u_29, (ref 5): v_u_30, (ref 6): v_u_31, (ref 7): v_u_32, (ref 8): v_u_33, (ref 9): v_u_34, (ref 10): v_u_35, (ref 11): v_u_36 ]]
    v_u_26 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_27 = require(game.ReplicatedStorage.Lobby.Menus.SongShopUI)
    v_u_28 = require(game.ReplicatedStorage.Lobby.Menus.LeaderboardsUI)
    v_u_29 = require(game.ReplicatedStorage.Lobby.Menus.SongInventoryV2UI)
    v_u_30 = require(game.ReplicatedStorage.Lobby.Menus.CraftingUI)
    v_u_31 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabSongs)
    v_u_32 = require(game.ReplicatedStorage.Lobby.Menus.CraftSongUI)
    v_u_33 = require(game.ReplicatedStorage.Lobby.Menus.VIPPurchaseUI)
    v_u_34 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_35 = require(game.ReplicatedStorage.Lobby.Menus.DJRequestUI)
    v_u_36 = require(game.ReplicatedStorage.Lobby.Menus.ColorSelectUI)
end)
local v_u_69 = {
    ["RecommendationType"] = {
        ["DailyMission"] = 1,
        ["WeeklyMission"] = 2,
        ["Leaderboard"] = 3,
        ["SongShop"] = 4,
        ["RecentlyAcquired"] = 5,
        ["JoinMatch"] = 6,
        ["SpectateMatch"] = 7,
        ["DJClubSong"] = 8,
        ["SongShopSale"] = 9,
        ["EasyMode"] = 10,
        ["ArtistEvent"] = 11
    },
    ["SongRecommendation"] = {
        ["new"] = function(_, p_u_37, p_u_38) --[[ Name: new ]] --[[ Line: 90 ]]
            --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_7, (copy 3): v_u_70 ]]
            local v39 = {}
            v_u_6:is_true(v_u_7:singleton():contains_key(p_u_37), string.format("SongDatabase does not contain songkey(%s)", (tostring(p_u_37))))
            v_u_6:is_enum_member(p_u_38, v_u_70)
            v39.get_songkey = function(_) --[[ Name: get_songkey ]] --[[ Line: 95 ]]
                --[[ Upvalues: (copy 1): p_u_37 ]]
                return p_u_37;
            end;
            v39.get_recommendation_type = function(_) --[[ Name: get_recommendation_type ]] --[[ Line: 96 ]]
                --[[ Upvalues: (copy 1): p_u_38 ]]
                return p_u_38;
            end;
            local v_u_40 = nil
            v39.set_data = function(p41, p42) --[[ Name: set_data ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_40 ]]
                v_u_40 = p42
                return p41;
            end;
            v39.get_data = function(_) --[[ Name: get_data ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_40 ]]
                return v_u_40;
            end;
            return v39;
        end
    },
    ["ListElement"] = {},
    ["PlayerListInfo"] = v24,
    ["AudioModFilterComponent"] = {
        ["reset_filter_state"] = function(_, p222) --[[ Name: reset_filter_state ]] --[[ Line: 860 ]]
            --[[ Upvalues: (copy 1): v_u_20 ]]
            p222:add(v_u_20.Easy, true)
            p222:add(v_u_20.Normal, true)
            p222:add(v_u_20.Hard, true)
        end,
        ["create_audiomod_filter_buttons"] = function(_, p_u_223, p_u_224, p_u_225, p_u_226, p_u_227, p228, p229, p230, p_u_231, p_u_232) --[[ Name: create_audiomod_filter_buttons ]] --[[ Line: 872 ]]
            --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4, (copy 3): v_u_3, (copy 4): v_u_5, (copy 5): v_u_20 ]]
            local v_u_233 = {}
            local v_u_234 = v_u_2:new()
            local function f_create_button(p235, p_u_236) --[[ Name: create_button ]] --[[ Line: 887 ]]
                --[[ Upvalues: (copy 1): p_u_227, (copy 2): p_u_224, (copy 3): p_u_223, (ref 4): v_u_4, (ref 5): v_u_3, (copy 6): p_u_225, (ref 7): v_u_5, (ref 8): v_u_20, (copy 9): p_u_226, (copy 10): v_u_233, (copy 11): p_u_232, (copy 12): v_u_234, (copy 13): p_u_231 ]]
                local v237 = p235:Clone()
                v237.Parent = p_u_227
                local v244 = p_u_224:add_cycle_element(p_u_223, 1, v_u_4:new(v_u_3:new(p_u_224, p_u_225, v237), p_u_223._spui, function() --[[ Line: 895 ]]
                    --[[ Upvalues: (ref 1): p_u_223, (ref 2): v_u_5, (ref 3): v_u_20, (ref 4): p_u_226, (copy 5): p_u_236, (ref 6): v_u_233, (ref 7): p_u_232, (ref 8): p_u_224 ]]
                    p_u_223._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
                    local v238 = true
                    for _, v239 in v_u_20:name_to_mod_itr() do
                        if p_u_226:get(v239) ~= true then
                            v238 = false
                            break;
                        end;
                    end;
                    local v240 = p_u_226:get(p_u_236)
                    if v238 then
                        for _, v241 in v_u_20:name_to_mod_itr() do
                            p_u_226:add(v241, false)
                        end;
                        p_u_226:add(p_u_236, true)
                    elseif v240 then
                        for _, v242 in v_u_20:name_to_mod_itr() do
                            p_u_226:add(v242, true)
                        end;
                    else
                        for _, v243 in v_u_20:name_to_mod_itr() do
                            p_u_226:add(v243, false)
                        end;
                        p_u_226:add(p_u_236, true)
                    end;
                    v_u_233:update_toggle_state()
                    p_u_232()
                    p_u_224:reset_page()
                    p_u_224:refresh_current_page()
                end)):set_auto_zoffset_behaviour(true)
                local v245 = v_u_4:button_bind_anim_toggle(v244, function() --[[ Line: 928 ]]
                    --[[ Upvalues: (ref 1): p_u_224 ]]
                    return p_u_224:get_alpha();
                end)
                v245:set_toggle_off_alpha(0.3)
                v_u_234:add(p_u_236, v245)
                v245:set_toggle(p_u_226:get(p_u_236))
                p_u_231(v244)
            end;
            f_create_button(p228, v_u_20.Easy)
            f_create_button(p229, v_u_20.Normal)
            f_create_button(p230, v_u_20.Hard)
            v_u_233.update_toggle_state = function(_) --[[ Name: update_toggle_state ]] --[[ Line: 939 ]]
                --[[ Upvalues: (ref 1): v_u_20, (copy 2): v_u_234, (copy 3): p_u_226 ]]
                for _, v246 in v_u_20:name_to_mod_itr() do
                    v_u_234:get(v246):set_toggle(p_u_226:get(v246))
                end;
            end;
            return v_u_233;
        end
    },
    ["FilterColorComponent"] = {
        ["reset_filter_state"] = function(_, p249) --[[ Name: reset_filter_state ]] --[[ Line: 949 ]]
            p249:clear()
        end,
        ["create_filter_state"] = function(_) --[[ Name: create_filter_state ]] --[[ Line: 953 ]]
            --[[ Upvalues: (copy 1): v_u_1 ]]
            return v_u_1:new();
        end
    }
}
local v_u_70 = {
    ["DailyMission"] = 1,
    ["WeeklyMission"] = 2,
    ["Leaderboard"] = 3,
    ["SongShop"] = 4,
    ["RecentlyAcquired"] = 5,
    ["JoinMatch"] = 6,
    ["SpectateMatch"] = 7,
    ["DJClubSong"] = 8,
    ["SongShopSale"] = 9,
    ["EasyMode"] = 10,
    ["ArtistEvent"] = 11
}
local v_u_71 = {
    ["PlaySong"] = 1,
    ["GoToSongShopPage"] = 2,
    ["GoToLeaderboardPage"] = 3,
    ["GoToCombinePage"] = 4,
    ["GoToCraftPage"] = 5,
    ["GoToVIPPage"] = 6,
    ["JoinMatch"] = 7,
    ["SpectateMatch"] = 8,
    ["DJClubSong"] = 9
}
({}).new = function(_, p_u_72, p_u_73, p_u_74, p_u_75, p_u_76, p_u_77) --[[ Name: new ]] --[[ Line: 105 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_71, (copy 3): v_u_9, (copy 4): v_u_20, (copy 5): v_u_7, (copy 6): v_u_11, (copy 7): v_u_8, (copy 8): v_u_22, (copy 9): v_u_69, (copy 10): v_u_16, (copy 11): v_u_17, (copy 12): v_u_19, (copy 13): v_u_14, (copy 14): v_u_70, (copy 15): v_u_12, (copy 16): v_u_18, (copy 17): v_u_21, (copy 18): v_u_10, (copy 19): v_u_6 ]]
    local v_u_78 = {}
    local v_u_79 = nil
    local v_u_80 = nil
    local v_u_81 = nil
    local v_u_82 = nil
    local v_u_83 = nil
    local v_u_84 = nil
    local v_u_85 = nil
    local v_u_86 = nil
    local v_u_87 = nil
    local v_u_88 = nil
    local v_u_89 = nil
    local v_u_90 = v_u_1:new()
    local v_u_91 = nil
    local l_PlaySong_0 = v_u_71.PlaySong
    local v_u_92 = -1
    local v_u_93 = -1
    v_u_78.cons = function(_) --[[ Name: cons ]] --[[ Line: 120 ]]
        --[[ Upvalues: (ref 1): v_u_79, (copy 2): p_u_74, (ref 3): v_u_80, (ref 4): v_u_81, (ref 5): v_u_82, (ref 6): v_u_88, (ref 7): v_u_89, (ref 8): v_u_9, (ref 9): v_u_83, (ref 10): v_u_84, (ref 11): v_u_85, (ref 12): v_u_86, (ref 13): v_u_87, (copy 14): v_u_90 ]]
        v_u_79 = p_u_74.SongImageButton.SurfaceGui.Frame.Icon
        v_u_80 = p_u_74.SongImageButton.SurfaceGui.Frame.IconOverlay
        v_u_81 = p_u_74.SongImageButton.SurfaceGui.Frame.Background
        v_u_82 = p_u_74.SongImageButton.SurfaceGui.Frame.ColorSection
        v_u_88 = p_u_74.SelectButton.SurfaceGui.Frame.Display
        v_u_89 = p_u_74.SelectButton.SurfaceGui.Frame.ButtonIcon
        v_u_89.Name = v_u_9:r_set_alpha_generate_name({
            ["ImageAlpha"] = 0.25
        }, v_u_89.Name)
        local l_Frame_0 = p_u_74.MainSurface.SurfaceGui.Frame
        v_u_83 = l_Frame_0.DescriptionText.Display
        v_u_84 = l_Frame_0.IconDisplay
        v_u_85 = l_Frame_0.BarSection.ProgressBarFill
        v_u_86 = l_Frame_0.BarSection.BarText
        v_u_87 = Vector2.new(v_u_85.Size.X.Offset, v_u_85.Size.Y.Offset)
        v_u_90:push_back_table_list({ l_Frame_0.InfoSection1, l_Frame_0.InfoSection2, l_Frame_0.InfoSection3 })
    end;
    Vector2.new(437, 24)
    Vector2.new(394, 16)
    local v_u_94 = nil
    v_u_78.set_bar_num_div = function(_, p95, p96, p97) --[[ Name: set_bar_num_div ]] --[[ Line: 144 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_94, (ref 3): v_u_86, (ref 4): v_u_85, (ref 5): v_u_87 ]]
        local v98 = v_u_9:clamp(p95 / p96, 0, 1)
        if v_u_94 ~= p97 then
            if p97 then
                v_u_86.Text = p97
            else
                v_u_86.Text = string.format("%s / %s", v_u_9:comma_value(p95), v_u_9:comma_value(p96))
            end;
            v_u_94 = v_u_86.Text
            v_u_85.Size = UDim2.new(0, v_u_87.X * v98, 0, v_u_87.Y)
        end;
    end;
    v_u_78.layout = function(_) --[[ Name: layout ]] --[[ Line: 158 ]]
        --[[ Upvalues: (copy 1): p_u_75 ]]
        p_u_75:layout()
    end;
    local v_u_99 = true
    v_u_78.set_visible = function(_, p100) --[[ Name: set_visible ]] --[[ Line: 163 ]]
        --[[ Upvalues: (ref 1): v_u_99, (copy 2): p_u_75, (copy 3): p_u_76, (copy 4): p_u_77 ]]
        v_u_99 = p100
        p_u_75:set_visible(p100)
        p_u_76:set_visible(p100)
        p_u_77:set_visible(p100)
    end;
    local function _(p101) --[[ Name: set_infosection_hidden ]] --[[ Line: 170 ]]
        p101.Visible = false
    end;
    local function _(p102, p103, p104) --[[ Name: set_infosection_to_text ]] --[[ Line: 174 ]]
        p102.Visible = true
        p102.NameDisplay.Text = p103
        p102.ValueTextDisplay.Visible = false
        p102.ValueTextDisplayCentered.Visible = true
        p102.ValueTextDisplayCentered.Text = p104
        p102.ValueTextIcon.Visible = false
        p102.ValueImageIcon.Visible = false
    end;
    local function f_set_infosection_to_song_difficulty(p105) --[[ Name: set_infosection_to_song_difficulty ]] --[[ Line: 184 ]]
        --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_7, (ref 3): v_u_91 ]]
        local v106 = tostring(v_u_7:singleton():get_difficulty_for_key(v_u_91:get_songkey())) .. " " .. string.format("(%s)", v_u_20:mod_to_name(v_u_7:singleton():key_get_audiomod(v_u_91:get_songkey())))
        p105.Visible = true
        p105.NameDisplay.Text = "Song Difficulty"
        p105.ValueTextDisplay.Visible = false
        p105.ValueTextDisplayCentered.Visible = true
        p105.ValueTextDisplayCentered.Text = v106
        p105.ValueTextIcon.Visible = false
        p105.ValueImageIcon.Visible = false
    end;
    local function _(p107) --[[ Name: set_infosection_to_mission_difficulty ]] --[[ Line: 193 ]]
        --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_91 ]]
        p107.Visible = true
        p107.NameDisplay.Text = "Mission Difficulty"
        p107.ValueTextDisplay.Visible = false
        p107.ValueTextDisplayCentered.Visible = false
        p107.ValueTextIcon.Visible = false
        p107.ValueImageIcon.Visible = true
        v_u_11:render_difficulty_image(p107.ValueImageIcon, v_u_11:mission_get_difficulty(v_u_91:get_data()))
    end;
    local function _(p108, p109, p110, p111) --[[ Name: set_infosection_to_price ]] --[[ Line: 203 ]]
        --[[ Upvalues: (ref 1): v_u_8 ]]
        p108.Visible = true
        p108.NameDisplay.Text = p109
        p108.ValueTextDisplay.Visible = true
        p108.ValueTextDisplayCentered.Visible = false
        p108.ValueTextDisplay.Text = tostring(p111)
        p108.ValueTextIcon.Visible = true
        v_u_8:currency_type_render_icon(p110, p108.ValueTextIcon)
        p108.ValueImageIcon.Visible = false
    end;
    local function f_set_infosection_to_mission_reward(p112) --[[ Name: set_infosection_to_mission_reward ]] --[[ Line: 214 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_91 ]]
        local v113 = v_u_22.MissionData:from_table(v_u_91:get_data())
        p112.Visible = true
        p112.NameDisplay.Text = "Mission Reward"
        p112.ValueTextDisplay.Visible = true
        p112.ValueTextDisplay.Text = tostring(v113:get_reward_amount())
        p112.ValueTextDisplayCentered.Visible = false
        p112.ValueTextIcon.Visible = true
        p112.ValueTextIcon.Image = v113:get_reward_image()
        p112.ValueImageIcon.Visible = false
    end;
    local function _(p114) --[[ Name: set_infosection_to_loading ]] --[[ Line: 227 ]]
        p114.Visible = true
        p114.NameDisplay.Text = ""
        p114.ValueTextDisplay.Visible = false
        p114.ValueTextDisplayCentered.Visible = true
        p114.ValueTextDisplayCentered.Text = "Loading..."
        p114.ValueTextIcon.Visible = false
        p114.ValueImageIcon.Visible = false
    end;
    local function f_update_selected_button_for_songkey(p115) --[[ Name: update_selected_button_for_songkey ]] --[[ Line: 237 ]]
        --[[ Upvalues: (copy 1): p_u_76, (ref 2): v_u_69, (copy 3): p_u_72, (ref 4): v_u_91, (copy 5): p_u_73, (ref 6): v_u_88, (ref 7): v_u_89, (ref 8): l_PlaySong_0, (ref 9): v_u_92, (ref 10): v_u_93, (ref 11): v_u_71 ]]
        p_u_76:set_visible(true)
        local v116 = v_u_69:get_recommendation_button_action_data_for_songkey(p_u_72, p115, v_u_91:get_recommendation_type(), {
            ["FilterPlayableOnly"] = p_u_73:filter_playable_only()
        })
        if v116.DidSet then
            v_u_88.Image = v116.TextImage
            v_u_89.Image = v116.IconImage
            l_PlaySong_0 = v116.SelectedButtonAction
            v_u_92 = v116.SelectedButtonSongkey
            v_u_93 = v116.SelectedButtonData
        else
            p_u_76:set_visible(false)
            l_PlaySong_0 = v_u_71.PlaySong
            v_u_92 = -1
            v_u_93 = -1
        end;
    end;
    local function f_update_mission_info(p117, p118, p119) --[[ Name: update_mission_info ]] --[[ Line: 262 ]]
        --[[ Upvalues: (ref 1): v_u_91, (copy 2): p_u_72, (ref 3): v_u_8, (copy 4): v_u_90, (ref 5): v_u_11, (copy 6): f_set_infosection_to_mission_reward, (copy 7): f_update_selected_button_for_songkey, (ref 8): v_u_7, (ref 9): l_PlaySong_0, (ref 10): v_u_71, (ref 11): v_u_92, (copy 12): v_u_78, (ref 13): v_u_83, (ref 14): v_u_16, (ref 15): v_u_17 ]]
        local v120 = v_u_91:get_data()
        local v121 = p_u_72._player_blob_manager:get_player_blob()
        local v122 = v_u_8:get_song_key_owned_count(v121, p117:get_songkey())
        local v123 = v_u_90:get(2)
        v123.Visible = true
        v123.NameDisplay.Text = "Mission Difficulty"
        v123.ValueTextDisplay.Visible = false
        v123.ValueTextDisplayCentered.Visible = false
        v123.ValueTextIcon.Visible = false
        v123.ValueImageIcon.Visible = true
        v_u_11:render_difficulty_image(v123.ValueImageIcon, v_u_11:mission_get_difficulty(v_u_91:get_data()))
        f_set_infosection_to_mission_reward(v_u_90:get(3))
        f_update_selected_button_for_songkey(p117:get_songkey())
        local v124 = v_u_7:singleton():key_is_fusionresult_of(p117:get_songkey())
        local v125 = not v_u_7:singleton():contains_key(v124) and 0 or v_u_8:get_song_key_owned_count(v121, v124)
        if l_PlaySong_0 == v_u_71.GoToSongShopPage then
            if p117:get_songkey() == v_u_92 then
                v_u_78:set_bar_num_div(v122, 1)
                v_u_83.Text = string.format("This song is required for a %s mission. Buy it from the store!", p118)
            else
                v_u_78:set_bar_num_div(v125, 5)
                v_u_83.Text = string.format("This song is required for a %s mission. Buy it from the store!", p118)
            end;
        elseif l_PlaySong_0 == v_u_71.GoToCraftPage then
            if p117:get_songkey() == v_u_92 then
                v_u_78:set_bar_num_div(v122, 1)
                v_u_83.Text = string.format("This song is required for a %s mission. Craft it!", p118)
            else
                v_u_78:set_bar_num_div(v125, 5)
                v_u_83.Text = string.format("This song is required for a %s mission. Craft copies of the normal mode!", p118)
            end;
        elseif l_PlaySong_0 == v_u_71.GoToCombinePage then
            v_u_78:set_bar_num_div(v125, 5)
            v_u_83.Text = string.format("This song is required for a %s mission.", p118)
            return;
        elseif l_PlaySong_0 == v_u_71.GoToVIPPage then
            v_u_78:set_bar_num_div(v122, 1)
            v_u_83.Text = string.format("This song is required for a %s mission. Get VIP to get access to every song!", p118)
        else
            local v126 = v_u_11:playerblob_missionid_get_count(v121, p119, v_u_11:mission_get_id(v120))
            local v127 = v_u_11:mission_get_count(v120)
            if v_u_11:mission_get_type(v120) == v_u_16.Rank then
                v_u_78:set_bar_num_div(v126, v127, string.format("%s", v_u_17:get_rank_value_name((v_u_17:index_to_rank_value(v126)))))
            else
                v_u_78:set_bar_num_div(v126, v127)
            end;
            v_u_83.Text = p118 .. " Mission: " .. v_u_11:get_mission_description_text(v120)
        end;
    end;
    local v_u_128 = -1
    v_u_78.display_recommendation = function(p_u_129, p_u_130) --[[ Name: display_recommendation ]] --[[ Line: 317 ]]
        --[[ Upvalues: (copy 1): p_u_72, (ref 2): v_u_128, (ref 3): v_u_91, (ref 4): v_u_7, (ref 5): v_u_79, (ref 6): v_u_80, (ref 7): v_u_19, (ref 8): v_u_82, (copy 9): f_set_infosection_to_song_difficulty, (copy 10): v_u_90, (ref 11): v_u_14, (ref 12): v_u_70, (ref 13): v_u_84, (copy 14): f_update_mission_info, (ref 15): v_u_83, (copy 16): p_u_76, (ref 17): v_u_99, (ref 18): v_u_12, (ref 19): v_u_8, (ref 20): v_u_9, (ref 21): v_u_88, (ref 22): v_u_89, (ref 23): l_PlaySong_0, (ref 24): v_u_71, (ref 25): v_u_92, (ref 26): v_u_93, (copy 27): f_update_selected_button_for_songkey, (ref 28): v_u_18, (ref 29): v_u_21, (ref 30): v_u_10 ]]
        if p_u_130 == nil then
            p_u_129:set_visible(false)
        end;
        local v_u_131 = p_u_72._player_blob_manager:get_global_time_float()
        v_u_128 = v_u_131
        v_u_91 = p_u_130
        v_u_7:singleton():render_coverimage_for_key(v_u_79, v_u_80, p_u_130:get_songkey())
        v_u_19:render_songkey_colorsection(p_u_130:get_songkey(), v_u_82)
        f_set_infosection_to_song_difficulty(v_u_90:get(1))
        local v_u_132 = v_u_91:get_data()
        local v133 = v_u_91:get_recommendation_type()
        local v_u_134 = v_u_14:playerblob_has_access_to_song(p_u_72._player_blob_manager:get_player_blob(), p_u_130:get_songkey(), p_u_72._player_blob_manager:get_day_id(), p_u_72._player_blob_manager:get_cached_collection_info())
        local v135 = v_u_134 == true and 1 or 0
        if v133 == v_u_70.DailyMission then
            v_u_84.Image = "rbxassetid://1138396569"
            v_u_84.Size = UDim2.new(0, 33, 0, 42)
            f_update_mission_info(p_u_130, "Daily", v_u_70.DailyMission)
            return;
        elseif v133 == v_u_70.WeeklyMission then
            v_u_84.Image = "rbxassetid://1138396570"
            v_u_84.Size = UDim2.new(0, 36, 0, 42)
            f_update_mission_info(p_u_130, "Weekly", v_u_70.WeeklyMission)
            return;
        elseif v133 == v_u_70.Leaderboard then
            v_u_84.Image = "rbxassetid://2038786453"
            v_u_84.Size = UDim2.new(0, 52, 0, 42)
            local v136 = v_u_90:get(2)
            v136.Visible = true
            v136.NameDisplay.Text = ""
            v136.ValueTextDisplay.Visible = false
            v136.ValueTextDisplayCentered.Visible = true
            v136.ValueTextDisplayCentered.Text = "Loading..."
            v136.ValueTextIcon.Visible = false
            v136.ValueImageIcon.Visible = false
            local v137 = v_u_90:get(3)
            v137.Visible = true
            v137.NameDisplay.Text = ""
            v137.ValueTextDisplay.Visible = false
            v137.ValueTextDisplayCentered.Visible = true
            v137.ValueTextDisplayCentered.Text = "Loading..."
            v137.ValueTextIcon.Visible = false
            v137.ValueImageIcon.Visible = false
            p_u_129:set_bar_num_div(0, 1, "Loading...")
            v_u_83.Text = "Loading..."
            p_u_76:set_visible(false)
            p_u_72._shop_local_protocol:leaderboard_query_song_index_cached(v_u_132.SongIndex, function(p138) --[[ Line: 353 ]]
                --[[ Upvalues: (ref 1): v_u_99, (copy 2): v_u_131, (ref 3): v_u_128, (ref 4): p_u_76, (copy 5): v_u_134, (ref 6): v_u_12, (copy 7): p_u_130, (ref 8): v_u_90, (ref 9): v_u_8, (ref 10): v_u_83, (copy 11): p_u_129, (ref 12): v_u_9, (copy 13): v_u_132, (ref 14): v_u_88, (ref 15): v_u_89, (ref 16): l_PlaySong_0, (ref 17): v_u_71, (ref 18): v_u_92, (ref 19): v_u_93, (ref 20): f_update_selected_button_for_songkey ]]
                if v_u_99 == true and v_u_131 == v_u_128 then
                    p_u_76:set_visible(true)
                    local v139 = true
                    local v140 = 0
                    if v_u_134 == true then
                        if p138.IsEntered == true then
                            local v141 = v_u_90:get(2)
                            local v142 = v_u_9:num_placify(p138.YouDisplay.Place)
                            v141.Visible = true
                            v141.NameDisplay.Text = "Rank"
                            v141.ValueTextDisplay.Visible = false
                            v141.ValueTextDisplayCentered.Visible = true
                            v141.ValueTextDisplayCentered.Text = v142
                            v141.ValueTextIcon.Visible = false
                            v141.ValueImageIcon.Visible = false
                            local v143 = v_u_90:get(3)
                            local v144 = tostring(p138.TotalParticipants)
                            v143.Visible = true
                            v143.NameDisplay.Text = "Total Participants"
                            v143.ValueTextDisplay.Visible = false
                            v143.ValueTextDisplayCentered.Visible = true
                            v143.ValueTextDisplayCentered.Text = v144
                            v143.ValueTextIcon.Visible = false
                            v143.ValueImageIcon.Visible = false
                            v140 = p138.YouDisplay.Place
                            v_u_83.Text = "This song is part of the weekly leaderboards. Get a new high score!"
                            v139 = false
                        else
                            local v145 = v_u_90:get(2)
                            local l_EntryPriceType_0 = v_u_132.EntryPriceType
                            local l_EntryPrice_0 = p138.EntryPrice
                            v145.Visible = true
                            v145.NameDisplay.Text = "Entry Cost"
                            v145.ValueTextDisplay.Visible = true
                            v145.ValueTextDisplayCentered.Visible = false
                            v145.ValueTextDisplay.Text = tostring(l_EntryPrice_0)
                            v145.ValueTextIcon.Visible = true
                            v_u_8:currency_type_render_icon(l_EntryPriceType_0, v145.ValueTextIcon)
                            v145.ValueImageIcon.Visible = false
                            v_u_90:get(3).Visible = false
                            v_u_83.Text = "This song is part of the weekly leaderboards. Enter the leaderboard and get a new high score!"
                        end;
                        local l_TotalParticipants_0 = p138.TotalParticipants
                        if v140 == 0 then
                            p_u_129:set_bar_num_div(0, l_TotalParticipants_0, "Not Placed")
                        else
                            p_u_129:set_bar_num_div(l_TotalParticipants_0 - v140, l_TotalParticipants_0, string.format("%s of %s", v_u_9:num_placify(v140), l_TotalParticipants_0))
                        end;
                    else
                        local v146, v147 = v_u_12:get_price_for_song(p_u_130:get_songkey())
                        local v148 = v_u_90:get(2)
                        v148.Visible = true
                        v148.NameDisplay.Text = "Song Cost"
                        v148.ValueTextDisplay.Visible = true
                        v148.ValueTextDisplayCentered.Visible = false
                        v148.ValueTextDisplay.Text = tostring(v147)
                        v148.ValueTextIcon.Visible = true
                        v_u_8:currency_type_render_icon(v146, v148.ValueTextIcon)
                        v148.ValueImageIcon.Visible = false
                        v_u_90:get(3).Visible = false
                        v_u_83.Text = "This song is required for the weekly leaderboards. Buy it from the leaderboard page!"
                        p_u_129:set_bar_num_div(0, 1)
                    end;
                    if v139 then
                        if v_u_134 then
                            v_u_88.Image = "rbxassetid://4887767298"
                            v_u_89.Image = v_u_9:get_iconhd_trophy()
                        else
                            v_u_88.Image = "rbxassetid://4944690483"
                            v_u_89.Image = v_u_9:get_iconhd_shop()
                        end;
                        l_PlaySong_0 = v_u_71.GoToLeaderboardPage
                        v_u_92 = p_u_130:get_songkey()
                        v_u_93 = v_u_132.SongIndex
                    else
                        f_update_selected_button_for_songkey(p_u_130:get_songkey())
                    end;
                else
                    return;
                end;
            end)
            return;
        elseif v133 == v_u_70.SongShop then
            v_u_84.Image = "rbxassetid://1149975134"
            v_u_84.Size = UDim2.new(0, 45, 0, 42)
            local v149 = v_u_90:get(2)
            local l_PriceType_0 = v_u_132.PriceType
            local l_PriceValue_0 = v_u_132.PriceValue
            v149.Visible = true
            v149.NameDisplay.Text = "Song Cost"
            v149.ValueTextDisplay.Visible = true
            v149.ValueTextDisplayCentered.Visible = false
            v149.ValueTextDisplay.Text = tostring(l_PriceValue_0)
            v149.ValueTextIcon.Visible = true
            v_u_8:currency_type_render_icon(l_PriceType_0, v149.ValueTextIcon)
            v149.ValueImageIcon.Visible = false
            local v150 = v_u_90:get(3)
            local v151 = tostring(v135)
            v150.Visible = true
            v150.NameDisplay.Text = "Owned Copies"
            v150.ValueTextDisplay.Visible = false
            v150.ValueTextDisplayCentered.Visible = true
            v150.ValueTextDisplayCentered.Text = v151
            v150.ValueTextIcon.Visible = false
            v150.ValueImageIcon.Visible = false
            v_u_83.Text = "This song is available to buy at the song shop today."
            p_u_129:set_bar_num_div(v135, 1)
            f_update_selected_button_for_songkey(p_u_130:get_songkey())
            return;
        elseif v133 == v_u_70.SongShopSale then
            v_u_82.Visible = false
            v_u_84.Image = "rbxassetid://1149975134"
            v_u_84.Size = UDim2.new(0, 45, 0, 42)
            local l_SaleComboKey_0 = v_u_132.SaleComboKey
            local v152 = v_u_90:get(2)
            local l_PriceType_1 = v_u_132.PriceType
            local l_PriceValue_1 = v_u_132.PriceValue
            v152.Visible = true
            v152.NameDisplay.Text = "Pack Cost"
            v152.ValueTextDisplay.Visible = true
            v152.ValueTextDisplayCentered.Visible = false
            v152.ValueTextDisplay.Text = tostring(l_PriceValue_1)
            v152.ValueTextIcon.Visible = true
            v_u_8:currency_type_render_icon(l_PriceType_1, v152.ValueTextIcon)
            v152.ValueImageIcon.Visible = false
            v_u_83.Text = string.format("Song pack \"%s\" is available for a limited time only!", v_u_18:get_title_for_saleid(l_SaleComboKey_0))
            f_update_selected_button_for_songkey(p_u_130:get_songkey())
            v_u_79.Image = v_u_18:get_shop_image_for_saleid(l_SaleComboKey_0)
            v_u_80.Image = v_u_9:transparent_assetid()
            p_u_129:set_bar_num_div(0, 1)
            v_u_90:get(3).Visible = false
            return;
        elseif v133 == v_u_70.RecentlyAcquired then
            v_u_84.Image = v_u_9:get_new_label_assetid()
            v_u_84.Size = UDim2.new(0, 45, 0, 20)
            v_u_83.Text = "Newly acquired song. Play now!"
            v_u_90:get(2).Visible = false
            v_u_90:get(3).Visible = false
            f_update_selected_button_for_songkey(p_u_130:get_songkey())
            p_u_129:set_bar_num_div(1, 1)
            return;
        elseif v133 == v_u_70.EasyMode then
            v_u_84.Image = "rbxassetid://7337181625"
            v_u_84.Size = UDim2.new(0, 65, 0, 20)
            v_u_83.Text = "Try out this easy mode song!"
            v_u_90:get(2).Visible = false
            v_u_90:get(3).Visible = false
            f_update_selected_button_for_songkey(p_u_130:get_songkey())
            p_u_129:set_bar_num_div(0, 1)
            return;
        elseif v133 == v_u_70.ArtistEvent then
            local v153, v154 = v_u_21:is_event_active(p_u_72._player_blob_manager:get_day_event_list())
            if v153 then
                v_u_84.Image = v_u_21:get_event_info(v154):get_icon()
            else
                v_u_84.Image = v_u_9:important_assetid()
            end;
            v_u_84.Size = UDim2.new(0, 50, 0, 50)
            v_u_83.Text = "Play this song to earn limited-time event points!"
            v_u_90:get(2).Visible = false
            v_u_90:get(3).Visible = false
            f_update_selected_button_for_songkey(p_u_130:get_songkey())
            p_u_129:set_bar_num_div(0, 1)
            return;
        elseif v133 == v_u_70.JoinMatch then
            local v155 = p_u_130:get_data()
            v_u_84.Image = v_u_9:transparent_assetid()
            v_u_84.Size = UDim2.new(0, 45, 0, 45)
            v_u_9:get_user_thumbnail(v155:get_player_id(), function(p156, _) --[[ Line: 471 ]]
                --[[ Upvalues: (ref 1): v_u_99, (copy 2): v_u_131, (ref 3): v_u_128, (ref 4): v_u_84 ]]
                if v_u_99 == true and v_u_131 == v_u_128 then
                    v_u_84.Image = p156
                end;
            end, false)
            v_u_83.Text = string.format("Player \"%s\" is in matchmaking for this song. Join now!", v155:get_name())
            v_u_90:get(2).Visible = false
            v_u_90:get(3).Visible = false
            p_u_129:set_bar_num_div(1, 1)
            v_u_88.Image = "rbxassetid://4887342879"
            v_u_89.Image = v_u_9:get_iconhd_song()
            l_PlaySong_0 = v_u_71.JoinMatch
            v_u_92 = v155:get_songkey()
            v_u_93 = v155
            p_u_76:set_visible(true)
            return;
        elseif v133 == v_u_70.SpectateMatch then
            local v157 = p_u_130:get_data()
            v_u_84.Image = v_u_9:transparent_assetid()
            v_u_84.Size = UDim2.new(0, 45, 0, 45)
            v_u_9:get_user_thumbnail(v157:get_player_id(), function(p158, _) --[[ Line: 493 ]]
                --[[ Upvalues: (ref 1): v_u_99, (copy 2): v_u_131, (ref 3): v_u_128, (ref 4): v_u_84 ]]
                if v_u_99 == true and v_u_131 == v_u_128 then
                    v_u_84.Image = p158
                end;
            end, false)
            v_u_83.Text = string.format("Player \"%s\" is playing this song. Click to spectate!", v157:get_name())
            local v159 = v_u_90:get(2)
            local v160 = tostring(v157:get_match_playercount())
            v159.Visible = true
            v159.NameDisplay.Text = "Match Players"
            v159.ValueTextDisplay.Visible = false
            v159.ValueTextDisplayCentered.Visible = true
            v159.ValueTextDisplayCentered.Text = v160
            v159.ValueTextIcon.Visible = false
            v159.ValueImageIcon.Visible = false
            v_u_90:get(3).Visible = false
            v_u_88.Image = "rbxassetid://4967795424"
            v_u_89.Image = v_u_9:get_iconhd_song()
            l_PlaySong_0 = v_u_71.SpectateMatch
            v_u_92 = v157:get_songkey()
            v_u_93 = v157
            p_u_76:set_visible(true)
            p_u_129:set_bar_num_div(v157:get_match_time_ms(), v157:get_song_length_ms(), string.format("%s / %s", v_u_9:format_ms_time(v157:get_match_time_ms()), v_u_9:format_ms_time(v157:get_song_length_ms())))
            return;
        elseif v133 == v_u_70.DJClubSong then
            v_u_84.Image = "rbxassetid://3124189703"
            v_u_84.Size = UDim2.new(0, 45, 0, 35)
            v_u_83.Text = string.format("This song is currently playing on Robeats Radio. Play it now for free!")
            v_u_90:get(2).Visible = false
            v_u_90:get(3).Visible = false
            v_u_88.Image = "rbxassetid://4887342879"
            v_u_89.Image = v_u_9:get_iconhd_song()
            l_PlaySong_0 = v_u_71.DJClubSong
            v_u_92 = p_u_130:get_songkey()
            v_u_93 = p_u_130:get_songkey()
            p_u_76:set_visible(true)
            local _, v161, v162, _ = p_u_72._dance_club_manager:get_current_song_info()
            p_u_129:set_bar_num_div(v161, v162, string.format("%s / %s", v_u_9:format_ms_time(v161 * 1000), v_u_9:format_ms_time(v162 * 1000)))
        else
            v_u_10:warnf("Unknown recommendation_type(%s)", (tostring(v133)))
        end;
    end;
    v_u_78.on_select_button_pressed = function(_) --[[ Name: on_select_button_pressed ]] --[[ Line: 546 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): l_PlaySong_0, (ref 3): v_u_71, (ref 4): v_u_69, (copy 5): p_u_72, (ref 6): v_u_92, (ref 7): v_u_93, (copy 8): p_u_73 ]]
        v_u_6:is_enum_member(l_PlaySong_0, v_u_71)
        v_u_69:perform_selected_button_action(p_u_72, l_PlaySong_0, v_u_92, v_u_93)
        p_u_73:get_play_ui():set_loading(true)
    end;
    v_u_78.behaviour_update = function(p163, _) --[[ Name: behaviour_update ]] --[[ Line: 559 ]]
        --[[ Upvalues: (ref 1): v_u_91, (ref 2): v_u_7, (copy 3): p_u_73, (ref 4): v_u_81, (ref 5): v_u_9, (ref 6): v_u_70, (copy 7): p_u_72 ]]
        if v_u_91 ~= nil then
            local v164 = v_u_91:get_songkey()
            if v164 == v_u_7:invalid_songkey() or v164 ~= p_u_73:get_play_ui():get_info_displayed_song_key() then
                v_u_81.Image = v_u_9:get_song_container_assetid()
            else
                v_u_81.Image = v_u_9:get_song_container_selected_assetid()
            end;
            if v_u_91:get_recommendation_type() == v_u_70.DJClubSong then
                local _, v165, v166, _ = p_u_72._dance_club_manager:get_current_song_info()
                p163:set_bar_num_div(v165, v166, string.format("%s / %s", v_u_9:format_ms_time(v165 * 1000), v_u_9:format_ms_time(v166 * 1000)))
                return;
            end;
            if v_u_91:get_recommendation_type() == v_u_70.SpectateMatch then
                local v167 = v_u_91:get_data()
                p163:set_bar_num_div(v167:get_match_time_ms(), v167:get_song_length_ms(), string.format("%s / %s", v_u_9:format_ms_time(v167:get_match_time_ms()), v_u_9:format_ms_time(v167:get_song_length_ms())))
            end;
        end;
    end;
    v_u_78.on_song_button_pressed = function(_) --[[ Name: on_song_button_pressed ]] --[[ Line: 590 ]]
        --[[ Upvalues: (ref 1): v_u_91, (ref 2): v_u_18, (ref 3): v_u_7, (copy 4): p_u_73 ]]
        if v_u_91 then
            local v168 = v_u_91:get_data()
            if typeof(v168) == "table" and v168.SaleComboKey ~= nil then
                local v169 = v_u_18:get_songids_for_saleid(v168.SaleComboKey):random()
                if v_u_7:singleton():contains_key(v169) then
                    p_u_73:get_play_ui():show_info_for_songkey(v169)
                    p_u_73:get_play_ui():play_preview_for_songkey(v169)
                    return;
                end;
            elseif v_u_7:singleton():contains_key(v_u_91:get_songkey()) then
                p_u_73:get_play_ui():show_info_for_songkey(v_u_91:get_songkey())
                p_u_73:get_play_ui():play_preview_for_songkey(v_u_91:get_songkey())
            end;
        end;
    end;
    v_u_78:cons()
    return v_u_78;
end
v_u_69.get_recommendation_button_action_data_for_songkey = function(_, p_u_170, p_u_171, p172, p173) --[[ Name: get_recommendation_button_action_data_for_songkey ]] --[[ Line: 611 ]]
    --[[ Upvalues: (copy 1): v_u_71, (copy 2): v_u_9, (copy 3): v_u_14, (copy 4): v_u_7, (copy 5): v_u_8, (copy 6): v_u_21, (copy 7): v_u_15, (copy 8): v_u_13, (copy 9): v_u_70 ]]
    local l_PlaySong_1 = v_u_71.PlaySong
    local v_u_174 = -1
    local v_u_175 = -1
    local v_u_176 = v_u_9:transparent_assetid()
    v_u_9:transparent_assetid()
    local v_u_177 = p_u_170._player_blob_manager:get_player_blob()
    local v_u_178 = v_u_14:playerblob_has_access_to_song(v_u_177, p_u_171, p_u_170._player_blob_manager:get_day_id(), p_u_170._player_blob_manager:get_cached_collection_info())
    local v_u_179 = false
    local v_u_180 = v_u_7:singleton():key_is_fusionresult_of(p_u_171)
    local v_u_181 = v_u_9:get_iconhd_song()
    local function f_song_shop_get_songkey_page(p182) --[[ Name: song_shop_get_songkey_page ]] --[[ Line: 629 ]]
        --[[ Upvalues: (copy 1): p_u_170, (ref 2): v_u_8 ]]
        local v183 = false
        local v184 = -1
        local v185 = p_u_170._player_blob_manager:get_player_blob()
        local v186 = p_u_170._player_blob_manager:get_server_song_shop_available_items_data()
        if v186 == nil then
            return v183, v184;
        end;
        for v187 = 1, #v186 do
            local v188 = v186[v187]
            if v188.SongKey == p182 then
                return v_u_8:get_count_for_song_shop_saleid(v185, v188.SaleId) == 0 and true or v183, v187;
            end;
        end;
        return v183, v184;
    end;
    local function f_opt_show_play() --[[ Name: opt_show_play ]] --[[ Line: 648 ]]
        --[[ Upvalues: (ref 1): v_u_179, (ref 2): v_u_21, (copy 3): p_u_170, (copy 4): p_u_171, (copy 5): v_u_178, (ref 6): v_u_176, (ref 7): v_u_181, (ref 8): v_u_9, (ref 9): l_PlaySong_1, (ref 10): v_u_71, (ref 11): v_u_174, (ref 12): v_u_175 ]]
        if v_u_179 == false then
            local v189, v190 = v_u_21:is_event_active(p_u_170._player_blob_manager:get_day_event_list())
            local v191
            if v189 then
                v191 = v_u_21:get_playable_song_set(v190):contains(p_u_171)
            else
                v191 = false
            end;
            if v_u_178 or v191 then
                v_u_176 = "rbxassetid://4887342879"
                v_u_181 = v_u_9:get_iconhd_song()
                l_PlaySong_1 = v_u_71.PlaySong
                v_u_174 = p_u_171
                v_u_175 = -1
                v_u_179 = true
            end;
        end;
    end;
    local function _() --[[ Name: opt_show_buy_songshop ]] --[[ Line: 667 ]]
        --[[ Upvalues: (ref 1): v_u_179, (copy 2): f_song_shop_get_songkey_page, (copy 3): p_u_171, (ref 4): v_u_176, (ref 5): v_u_181, (ref 6): v_u_9, (ref 7): l_PlaySong_1, (ref 8): v_u_71, (ref 9): v_u_174, (ref 10): v_u_175 ]]
        if v_u_179 == false then
            local v192, v193 = f_song_shop_get_songkey_page(p_u_171)
            if v192 == true then
                v_u_176 = "rbxassetid://4944690483"
                v_u_181 = v_u_9:get_iconhd_song()
                l_PlaySong_1 = v_u_71.GoToSongShopPage
                v_u_174 = p_u_171
                v_u_175 = v193
                v_u_179 = true
            end;
        end;
    end;
    local function f_opt_show_craft() --[[ Name: opt_show_craft ]] --[[ Line: 681 ]]
        --[[ Upvalues: (ref 1): v_u_179, (ref 2): v_u_15, (copy 3): v_u_177, (copy 4): p_u_171, (copy 5): p_u_170, (ref 6): v_u_13, (ref 7): v_u_176, (ref 8): v_u_181, (ref 9): v_u_9, (ref 10): l_PlaySong_1, (ref 11): v_u_71, (ref 12): v_u_174, (ref 13): v_u_175 ]]
        if v_u_179 == false and (v_u_15:can_craft_songkey(v_u_177, p_u_171, p_u_170._player_blob_manager:get_cached_collection_info()) and v_u_13:singleton():get_songkey_recipe_id(p_u_171) ~= nil) then
            v_u_176 = "rbxassetid://4887343122"
            v_u_181 = v_u_9:get_iconhd_crafting()
            l_PlaySong_1 = v_u_71.GoToCraftPage
            v_u_174 = p_u_171
            v_u_175 = -1
            v_u_179 = true
        end;
    end;
    local function f_opt_show_combine() --[[ Name: opt_show_combine ]] --[[ Line: 697 ]]
        --[[ Upvalues: (ref 1): v_u_179, (copy 2): v_u_180, (ref 3): v_u_7, (ref 4): v_u_8, (copy 5): v_u_177, (ref 6): v_u_176, (ref 7): v_u_181, (ref 8): v_u_9, (ref 9): l_PlaySong_1, (ref 10): v_u_71, (ref 11): v_u_174, (copy 12): p_u_171, (ref 13): v_u_175 ]]
        if v_u_179 == false and v_u_180 ~= nil then
            local v194, v195 = v_u_7:singleton():key_has_combineinfo(v_u_180)
            if v194 == true and v195.RequiredCount <= v_u_8:get_song_key_owned_count(v_u_177, v_u_180) then
                v_u_176 = "rbxassetid://4887343122"
                v_u_181 = v_u_9:get_iconhd_crafting()
                l_PlaySong_1 = v_u_71.GoToCombinePage
                v_u_174 = p_u_171
                v_u_175 = -1
                v_u_179 = true
            end;
        end;
    end;
    local function _() --[[ Name: opt_show_buy_songshop_fusioningredient ]] --[[ Line: 713 ]]
        --[[ Upvalues: (ref 1): v_u_179, (copy 2): v_u_180, (copy 3): f_song_shop_get_songkey_page, (ref 4): v_u_176, (ref 5): v_u_181, (ref 6): v_u_9, (ref 7): l_PlaySong_1, (ref 8): v_u_71, (ref 9): v_u_174, (copy 10): p_u_171, (ref 11): v_u_175 ]]
        if v_u_179 == false and v_u_180 ~= nil then
            local v196, v197 = f_song_shop_get_songkey_page(v_u_180)
            if v196 == true then
                v_u_176 = "rbxassetid://4944690483"
                v_u_181 = v_u_9:get_iconhd_shop()
                l_PlaySong_1 = v_u_71.GoToSongShopPage
                v_u_174 = p_u_171
                v_u_175 = v197
                v_u_179 = true
            end;
        end;
    end;
    local function f_opt_show_craft_fusioningredient() --[[ Name: opt_show_craft_fusioningredient ]] --[[ Line: 727 ]]
        --[[ Upvalues: (ref 1): v_u_179, (copy 2): v_u_180, (ref 3): v_u_13, (ref 4): v_u_15, (copy 5): v_u_177, (copy 6): p_u_170, (ref 7): v_u_176, (ref 8): v_u_181, (ref 9): v_u_9, (ref 10): l_PlaySong_1, (ref 11): v_u_71, (ref 12): v_u_174, (copy 13): p_u_171, (ref 14): v_u_175 ]]
        if v_u_179 == false and v_u_180 ~= nil and (v_u_15:can_craft_songkey(v_u_177, v_u_180, p_u_170._player_blob_manager:get_cached_collection_info()) and v_u_13:singleton():get_songkey_recipe_id(v_u_180) ~= nil) then
            v_u_176 = "rbxassetid://4887343122"
            v_u_181 = v_u_9:get_iconhd_crafting()
            l_PlaySong_1 = v_u_71.GoToCraftPage
            v_u_174 = p_u_171
            v_u_175 = -1
            v_u_179 = true
        end;
    end;
    local function _() --[[ Name: opt_show_get_vip ]] --[[ Line: 743 ]]
        --[[ Upvalues: (ref 1): v_u_179, (ref 2): v_u_176, (ref 3): v_u_181, (ref 4): v_u_9, (ref 5): l_PlaySong_1, (ref 6): v_u_71, (ref 7): v_u_174, (copy 8): p_u_171, (ref 9): v_u_175 ]]
        if v_u_179 == false then
            v_u_176 = "rbxassetid://4887730407"
            v_u_181 = v_u_9:get_iconhd_vip()
            l_PlaySong_1 = v_u_71.GoToVIPPage
            v_u_174 = p_u_171
            v_u_175 = -1
            v_u_179 = true
        end;
    end;
    local v198, v199, v200
    if p172 == v_u_70.SongShopSale then
        if v_u_179 == false then
            local v201, v202 = f_song_shop_get_songkey_page(p_u_171)
            if v201 == true then
                v198 = "rbxassetid://4944690483"
                v_u_181 = v_u_9:get_iconhd_song()
                l_PlaySong_1 = v_u_71.GoToSongShopPage
                v199 = p_u_171
                v200 = v202
                v_u_179 = true
            else
                v199 = v_u_174
                v198 = v_u_176
                v200 = v_u_175
            end;
        else
            v199 = v_u_174
            v198 = v_u_176
            v200 = v_u_175
        end;
    elseif p172 == v_u_70.SongShop and p173.FilterPlayableOnly ~= true then
        if v_u_179 == false then
            local v203, v204 = f_song_shop_get_songkey_page(p_u_171)
            if v203 == true then
                v198 = "rbxassetid://4944690483"
                v_u_181 = v_u_9:get_iconhd_song()
                l_PlaySong_1 = v_u_71.GoToSongShopPage
                v199 = p_u_171
                v200 = v204
                v_u_179 = true
            else
                v198 = v_u_176
                v200 = v_u_175
                v199 = v_u_174
            end;
        else
            v198 = v_u_176
            v200 = v_u_175
            v199 = v_u_174
        end;
        f_opt_show_play()
    else
        f_opt_show_play()
        if v_u_179 == false then
            local v205, v206 = f_song_shop_get_songkey_page(p_u_171)
            if v205 == true then
                v198 = "rbxassetid://4944690483"
                v_u_181 = v_u_9:get_iconhd_song()
                l_PlaySong_1 = v_u_71.GoToSongShopPage
                v199 = p_u_171
                v200 = v206
                v_u_179 = true
            else
                v199 = v_u_174
                v198 = v_u_176
                v200 = v_u_175
            end;
        else
            v199 = v_u_174
            v198 = v_u_176
            v200 = v_u_175
        end;
    end;
    f_opt_show_craft()
    f_opt_show_combine()
    if v_u_179 == false and v_u_180 ~= nil then
        local v207, v208 = f_song_shop_get_songkey_page(v_u_180)
        if v207 == true then
            v198 = "rbxassetid://4944690483"
            v_u_181 = v_u_9:get_iconhd_shop()
            l_PlaySong_1 = v_u_71.GoToSongShopPage
            v199 = p_u_171
            v200 = v208
            v_u_179 = true
        end;
    end;
    f_opt_show_craft_fusioningredient()
    if v_u_179 == false then
        v198 = "rbxassetid://4887730407"
        v_u_181 = v_u_9:get_iconhd_vip()
        l_PlaySong_1 = v_u_71.GoToVIPPage
        v199 = p_u_171
        v200 = -1
        v_u_179 = true
    end;
    return {
        ["DidSet"] = v_u_179,
        ["SelectedButtonAction"] = l_PlaySong_1,
        ["SelectedButtonSongkey"] = v199,
        ["SelectedButtonData"] = v200,
        ["TextImage"] = v198,
        ["IconImage"] = v_u_181
    };
end;
v_u_69.perform_selected_button_action = function(_, p_u_209, p210, p_u_211, p212) --[[ Name: perform_selected_button_action ]] --[[ Line: 780 ]]
    --[[ Upvalues: (copy 1): v_u_71, (copy 2): v_u_6, (copy 3): v_u_7, (ref 4): v_u_26, (ref 5): v_u_27, (ref 6): v_u_28, (ref 7): v_u_29, (ref 8): v_u_32, (copy 9): v_u_15, (ref 10): v_u_30, (ref 11): v_u_31, (ref 12): v_u_33, (ref 13): v_u_34, (ref 14): v_u_35 ]]
    local v213 = p_u_209._player_blob_manager:get_player_blob()
    if p210 == v_u_71.PlaySong then
        v_u_6:is_true(v_u_7:singleton():contains_key(p_u_211))
        p_u_209._menus:push_menu(v_u_26:new(p_u_209, p_u_209._spui, p_u_209._menus, p_u_211, nil))
        return;
    elseif p210 == v_u_71.GoToSongShopPage then
        v_u_6:is_int(p212)
        local v_u_214 = nil
        v_u_214 = v_u_27:new(p_u_209, p_u_209._spui, p_u_209._menus, p212, function(p215) --[[ Line: 800 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_211, (ref 3): v_u_214, (copy 4): p_u_209 ]]
            if v_u_7:singleton():get_all_modes_of_songkey(p_u_211):contains(p215) and v_u_214 ~= nil then
                p_u_209._menus:remove_menu(v_u_214)
            end;
        end)
        p_u_209._menus:push_menu(v_u_214)
        return;
    elseif p210 == v_u_71.GoToLeaderboardPage then
        v_u_6:is_int(p212)
        p_u_209._menus:push_menu(v_u_28:new(p_u_209, p_u_209._spui, p_u_209._menus, p212))
        return;
    elseif p210 == v_u_71.GoToCombinePage then
        v_u_6:is_true(v_u_7:singleton():contains_key(p_u_211))
        p_u_209._menus:push_menu(v_u_29:new(p_u_209, p_u_209._spui, p_u_209._menus, p_u_211))
        return;
    elseif p210 == v_u_71.GoToCraftPage then
        v_u_6:is_true(v_u_7:singleton():contains_key(p_u_211))
        local v216 = v_u_32:get_songkey_recipe_id(p_u_211)
        local v217
        if v216 == nil then
            v217 = false
        else
            v217 = v_u_15:can_craft_recipe(v213, v216)
        end;
        if v217 then
            p_u_209._menus:push_menu(v_u_32:new(p_u_209, p_u_209._spui, p_u_209._menus, p_u_211))
        else
            p_u_209._menus:push_menu(v_u_30:new(p_u_209, p_u_209._spui, p_u_209._menus, v_u_31.Tab, p_u_211))
        end;
    elseif p210 == v_u_71.GoToVIPPage then
        p_u_209._menus:push_menu(v_u_33:new(p_u_209, p_u_209._spui, p_u_209._menus))
        return;
    elseif p210 == v_u_71.JoinMatch then
        p_u_209._menus:push_menu(v_u_26:new(p_u_209, p_u_209._spui, p_u_209._menus, p212:get_songkey(), p212:get_player_id()))
        return;
    elseif p210 == v_u_71.SpectateMatch then
        local v_u_218 = p_u_209._menus:push_menu(v_u_34:new(p_u_209, p_u_209._spui, p_u_209._menus):set_text("Joining Match...", "Please wait..."):set_close_button_visible(false))
        p_u_209._spectate_manager:try_spectate_userid(p212:get_player_id(), function(p219, p220, p221) --[[ Line: 845 ]]
            --[[ Upvalues: (copy 1): p_u_209, (copy 2): v_u_218, (ref 3): v_u_34 ]]
            p_u_209._menus:remove_menu(v_u_218)
            if p219 ~= true then
                p_u_209._menus:push_menu(v_u_34:new(p_u_209, p_u_209._spui, p_u_209._menus):set_text("Error", p220))
            end;
            p221()
        end)
    elseif p210 == v_u_71.DJClubSong then
        p_u_209._menus:push_menu(v_u_35:new(p_u_209, p_u_209._spui, p_u_209._menus))
    end;
end;
local v_u_247 = {
    ["reset_filter_state"] = function(_, p222) --[[ Name: reset_filter_state ]] --[[ Line: 860 ]]
        --[[ Upvalues: (copy 1): v_u_20 ]]
        p222:add(v_u_20.Easy, true)
        p222:add(v_u_20.Normal, true)
        p222:add(v_u_20.Hard, true)
    end,
    ["create_audiomod_filter_buttons"] = function(_, p_u_223, p_u_224, p_u_225, p_u_226, p_u_227, p228, p229, p230, p_u_231, p_u_232) --[[ Name: create_audiomod_filter_buttons ]] --[[ Line: 872 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4, (copy 3): v_u_3, (copy 4): v_u_5, (copy 5): v_u_20 ]]
        local v_u_233 = {}
        local v_u_234 = v_u_2:new()
        local function f_create_button(p235, p_u_236) --[[ Name: create_button ]] --[[ Line: 887 ]]
            --[[ Upvalues: (copy 1): p_u_227, (copy 2): p_u_224, (copy 3): p_u_223, (ref 4): v_u_4, (ref 5): v_u_3, (copy 6): p_u_225, (ref 7): v_u_5, (ref 8): v_u_20, (copy 9): p_u_226, (copy 10): v_u_233, (copy 11): p_u_232, (copy 12): v_u_234, (copy 13): p_u_231 ]]
            local v237 = p235:Clone()
            v237.Parent = p_u_227
            local v244 = p_u_224:add_cycle_element(p_u_223, 1, v_u_4:new(v_u_3:new(p_u_224, p_u_225, v237), p_u_223._spui, function() --[[ Line: 895 ]]
                --[[ Upvalues: (ref 1): p_u_223, (ref 2): v_u_5, (ref 3): v_u_20, (ref 4): p_u_226, (copy 5): p_u_236, (ref 6): v_u_233, (ref 7): p_u_232, (ref 8): p_u_224 ]]
                p_u_223._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
                local v238 = true
                for _, v239 in v_u_20:name_to_mod_itr() do
                    if p_u_226:get(v239) ~= true then
                        v238 = false
                        break;
                    end;
                end;
                local v240 = p_u_226:get(p_u_236)
                if v238 then
                    for _, v241 in v_u_20:name_to_mod_itr() do
                        p_u_226:add(v241, false)
                    end;
                    p_u_226:add(p_u_236, true)
                elseif v240 then
                    for _, v242 in v_u_20:name_to_mod_itr() do
                        p_u_226:add(v242, true)
                    end;
                else
                    for _, v243 in v_u_20:name_to_mod_itr() do
                        p_u_226:add(v243, false)
                    end;
                    p_u_226:add(p_u_236, true)
                end;
                v_u_233:update_toggle_state()
                p_u_232()
                p_u_224:reset_page()
                p_u_224:refresh_current_page()
            end)):set_auto_zoffset_behaviour(true)
            local v245 = v_u_4:button_bind_anim_toggle(v244, function() --[[ Line: 928 ]]
                --[[ Upvalues: (ref 1): p_u_224 ]]
                return p_u_224:get_alpha();
            end)
            v245:set_toggle_off_alpha(0.3)
            v_u_234:add(p_u_236, v245)
            v245:set_toggle(p_u_226:get(p_u_236))
            p_u_231(v244)
        end;
        f_create_button(p228, v_u_20.Easy)
        f_create_button(p229, v_u_20.Normal)
        f_create_button(p230, v_u_20.Hard)
        v_u_233.update_toggle_state = function(_) --[[ Name: update_toggle_state ]] --[[ Line: 939 ]]
            --[[ Upvalues: (ref 1): v_u_20, (copy 2): v_u_234, (copy 3): p_u_226 ]]
            for _, v246 in v_u_20:name_to_mod_itr() do
                v_u_234:get(v246):set_toggle(p_u_226:get(v246))
            end;
        end;
        return v_u_233;
    end
}
v_u_247.create_filter_state = function(_) --[[ Name: create_filter_state ]] --[[ Line: 866 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_247 ]]
    local v248 = v_u_2:new()
    v_u_247:reset_filter_state(v248)
    return v248;
end;
local v_u_250 = {
    ["reset_filter_state"] = function(_, p249) --[[ Name: reset_filter_state ]] --[[ Line: 949 ]]
        p249:clear()
    end,
    ["create_filter_state"] = function(_) --[[ Name: create_filter_state ]] --[[ Line: 953 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:new();
    end
}
v_u_250.create_filter_button = function(_, p_u_251, p_u_252, p_u_253, p254, p_u_255, p_u_256, p_u_257) --[[ Name: create_filter_button ]] --[[ Line: 957 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3, (copy 3): v_u_5, (ref 4): v_u_36, (copy 5): v_u_23, (copy 6): v_u_250, (copy 7): v_u_9, (copy 8): v_u_19 ]]
    local v258 = {}
    local v_u_265 = (function(p259, p_u_260) --[[ Name: create_button_toggle ]] --[[ Line: 968 ]]
        --[[ Upvalues: (copy 1): p_u_253, (copy 2): p_u_252, (copy 3): p_u_251, (ref 4): v_u_4, (ref 5): v_u_3, (ref 6): v_u_5, (copy 7): p_u_256 ]]
        local v261 = p259:Clone()
        v261.Parent = p_u_253
        local v262 = p_u_252:add_cycle_element(p_u_251, 1, v_u_4:new(v_u_3:new(p_u_252, p_u_253.PrimaryPart, v261), p_u_251._spui, function() --[[ Line: 974 ]]
            --[[ Upvalues: (ref 1): p_u_251, (ref 2): v_u_5, (copy 3): p_u_260 ]]
            p_u_251._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            p_u_260()
        end)):set_auto_zoffset_behaviour(true)
        p_u_256(v262)
        return v_u_4:button_bind_anim_toggle(v262, function() --[[ Line: 980 ]]
            --[[ Upvalues: (ref 1): p_u_252 ]]
            return p_u_252:get_alpha();
        end);
    end)(p254, function() --[[ Line: 983 ]]
        --[[ Upvalues: (copy 1): p_u_257, (copy 2): p_u_252, (copy 3): p_u_251, (ref 4): v_u_36, (ref 5): v_u_23, (ref 6): v_u_250, (copy 7): p_u_255 ]]
        local function _() --[[ Name: filter_updated ]] --[[ Line: 984 ]]
            --[[ Upvalues: (ref 1): p_u_257, (ref 2): p_u_252 ]]
            p_u_257()
            p_u_252:reset_page()
            p_u_252:refresh_current_page()
        end;
        p_u_251._menus:push_menu(v_u_36:new(p_u_251, p_u_251._spui, p_u_251._menus, "Select Primary Element", "Select primary element to filter by.\nSelect \'None\' to clear the filter.", function(p_u_263) --[[ Line: 993 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_250, (ref 3): p_u_255, (ref 4): p_u_257, (ref 5): p_u_252, (ref 6): p_u_251, (ref 7): v_u_36 ]]
            if p_u_263 == v_u_23:color_none() then
                v_u_250:reset_filter_state(p_u_255)
                p_u_257()
                p_u_252:reset_page()
                p_u_252:refresh_current_page()
            else
                p_u_251._menus:push_menu(v_u_36:new(p_u_251, p_u_251._spui, p_u_251._menus, "Select Secondary Element", "Select the secondary element to filter by.\nSelect \'None\' to find any song with the selected primary element, or select the same element to find single-element songs.", function(p264) --[[ Line: 1002 ]]
                    --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_250, (ref 3): p_u_255, (copy 4): p_u_263, (ref 5): p_u_257, (ref 6): p_u_252 ]]
                    if p264 == v_u_23:color_none() then
                        v_u_250:reset_filter_state(p_u_255)
                        p_u_255:push_back(p_u_263)
                        p_u_257()
                        p_u_252:reset_page()
                        p_u_252:refresh_current_page()
                    else
                        v_u_250:reset_filter_state(p_u_255)
                        p_u_255:push_back(p_u_263)
                        p_u_255:push_back(p264)
                        p_u_257()
                        p_u_252:reset_page()
                        p_u_252:refresh_current_page()
                    end;
                end):set_none_selectable())
            end;
        end):set_none_selectable())
    end)
    local v266 = v_u_265:get_button():get_part()
    local l_PrimaryColorIcon_0 = v266.SurfaceGui.ColorSection.PrimaryColorIcon
    local l_SecondaryColorIcon_0 = v266.SurfaceGui.ColorSection.SecondaryColorIcon
    v258.update_state = function(_) --[[ Name: update_state ]] --[[ Line: 1024 ]]
        --[[ Upvalues: (copy 1): p_u_255, (copy 2): v_u_265, (copy 3): l_PrimaryColorIcon_0, (ref 4): v_u_23, (copy 5): l_SecondaryColorIcon_0, (ref 6): v_u_9 ]]
        if p_u_255:count() == 0 then
            v_u_265:set_toggle(false)
            l_PrimaryColorIcon_0.Image = v_u_23:color_to_iconimage(v_u_23.Blue)
            l_SecondaryColorIcon_0.Image = v_u_9:transparent_assetid()
            return;
        else
            v_u_265:set_toggle(true)
            if p_u_255:count() == 1 then
                l_PrimaryColorIcon_0.Image = v_u_23:color_to_iconimage((p_u_255:get(1)))
                l_SecondaryColorIcon_0.Image = v_u_9:transparent_assetid()
            elseif p_u_255:count() == 2 then
                local v267 = p_u_255:get(1)
                local v268 = p_u_255:get(2)
                l_PrimaryColorIcon_0.Image = v_u_23:color_to_iconimage(v267)
                if v267 ~= v268 then
                    l_SecondaryColorIcon_0.Image = v_u_23:color_to_iconimage(v268)
                    return;
                end;
                l_SecondaryColorIcon_0.Image = v_u_9:transparent_assetid()
            end;
        end;
    end;
    v258.get_filter_string = function(_) --[[ Name: get_filter_string ]] --[[ Line: 1049 ]]
        --[[ Upvalues: (copy 1): p_u_255 ]]
        local v269 = ""
        for v270 = 1, p_u_255:count() do
            v269 = v269 .. "_" .. tostring(p_u_255:get(v270))
        end;
        return v269;
    end;
    local v_u_271 = v_u_23:color_none()
    v258.get_filter_colors = function(_) --[[ Name: get_filter_colors ]] --[[ Line: 1058 ]]
        --[[ Upvalues: (copy 1): v_u_271, (copy 2): p_u_255 ]]
        local v272 = v_u_271
        local v273 = v_u_271
        local v274
        if p_u_255:count() >= 1 then
            v272 = p_u_255:get(1)
            v274 = true
        else
            v274 = false
        end;
        if p_u_255:count() >= 2 then
            v273 = p_u_255:get(2)
        end;
        return v274, v272, v273;
    end;
    v258.songkey_test_filter_colors = function(_, p275, p276, p277) --[[ Name: songkey_test_filter_colors ]] --[[ Line: 1072 ]]
        --[[ Upvalues: (copy 1): v_u_271, (ref 2): v_u_19 ]]
        local v278 = p277 ~= v_u_271
        local v279
        if p276 == v_u_271 then
            v279 = false
        else
            v279 = v278
        end;
        local v280 = p276 == p277
        local v281 = v_u_19:songkey_get_color_list(p275)
        if v281:count() <= 0 then
            return false;
        end;
        if v278 == true then
            if v280 == true then
                if v281:count() > 1 then
                    return false;
                end;
                if v281:get(1) ~= p276 then
                    return false;
                end;
            elseif v279 then
                if v281:count() < 2 then
                    return false;
                end;
                if v281:get(1) ~= p276 or v281:get(2) ~= p277 then
                    return false;
                end;
            end;
        elseif v281:get(1) ~= p276 then
            return false;
        end;
        return true;
    end;
    return v258;
end;
return v_u_69;
