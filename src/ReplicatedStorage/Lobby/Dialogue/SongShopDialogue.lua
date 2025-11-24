-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:58 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_5 = require(game.ReplicatedStorage.Menu.CharacterDialogue)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v8 = {}
local v_u_9 = false
local v_u_10 = v2:new():push_back_table_list({
    {
        ["Mattie"] = "Hey! I think you\'ll LOVE what we\'ve got for you today.",
        ["Marie"] = "I hope you can find something you like.",
        ["Firsttime"] = true
    },
    {
        ["Mattie"] = "Welcome back! Ready to buy some more songs?",
        ["Marie"] = "Nice to see you again."
    }
})
local v_u_11 = v2:new():push_back_table_list({
    {
        ["Mattie"] = "One of the easier songs, but it\'s a vibe.",
        ["Songname"] = "MarkTwain1"
    },
    {
        ["Mattie"] = "I heard a certain friendly alien made the game this comes from...",
        ["Songname"] = "MondayNightMonsters1"
    },
    {
        ["Mattie"] = "You might recognize this song as being made by a quite prolific community mapper.",
        ["Songname"] = "Jungle1"
    },
    {
        ["Mattie"] = "This was one of the first songs made by our talented community members.",
        ["Songname"] = "Rotatsu1"
    },
    {
        ["Marie"] = "The start of one of the most iconic rhythm games of our time!",
        ["Songname"] = "FNFBopeebo1"
    },
    {
        ["Marie"] = "I\'m sure we\'ve all heard this somewhere before...",
        ["Songname"] = "StadiumRave1"
    }
})
local v_u_12 = v2:new():push_back_table_list({
    {
        ["Mattie"] = "We get new songs every day! Sometimes Marie even lets me pick \'em out!"
    },
    {
        ["Mattie"] = "You wouldn\'t BELIEVE how many complainers we get. Can\'t make \'em all happy, right?"
    },
    {
        ["Mattie"] = "Would you guess that Marie and I are sisters? We started this shop together!"
    },
    {
        ["Mattie"] = "Not enough coins? Go get some by playing songs and doing missions!"
    },
    {
        ["Marie"] = "Do you like the songs I picked? I tried not to make them all too hard."
    },
    {
        ["Marie"] = "What kind of songs do you like? For me... depends on how I\'m feeling at the moment."
    },
    {
        ["Marie"] = "Have you heard this song before? You should if you haven\'t... I think it\'s pretty good."
    },
    {
        ["Marie"] = "Even if you don\'t think you like something... you should still try it out. You never know, right?"
    }
})
local v_u_13 = v2:new():push_back_table_list({
    {
        ["Mattie"] = "That\'s a great choice!",
        ["Marie"] = "That\'s a good one. Let me know what you think."
    }
})
v8.new = function(_, p_u_14, p_u_15, p_u_16, p_u_17) --[[ Name: new ]] --[[ Line: 56 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_6, (copy 5): v_u_7, (copy 6): v_u_1, (copy 7): v_u_11, (copy 8): v_u_13, (copy 9): v_u_10, (ref 10): v_u_9, (copy 11): v_u_12 ]]
    local v18 = {}
    local v_u_19 = nil
    local v_u_20 = nil
    local v_u_21 = nil
    local v_u_22 = nil
    v18.cons = function(p_u_23) --[[ Name: cons ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_5, (copy 3): p_u_17, (ref 4): v_u_3, (copy 5): p_u_16, (ref 6): v_u_20, (ref 7): v_u_21, (copy 8): p_u_15, (copy 9): p_u_14, (ref 10): v_u_4, (ref 11): v_u_6, (ref 12): v_u_22 ]]
        v_u_19 = v_u_5:new("Mattie", p_u_17.MattieDialogue, v_u_3:new(p_u_16, p_u_17.PrimaryPart, p_u_17.MattieDialogue))
        v_u_20 = v_u_5:new("Marie", p_u_17.MarieDialogue, v_u_3:new(p_u_16, p_u_17.PrimaryPart, p_u_17.MarieDialogue))
        v_u_21 = p_u_15:add_cycle_element(p_u_14, 1, v_u_4:new(v_u_3:new(p_u_15, p_u_17.PrimaryPart, p_u_17.Mattie), p_u_14._spui, function() --[[ Line: 81 ]]
            --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_6, (copy 3): p_u_23 ]]
            p_u_14._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            p_u_23:load_from_pressed_dialogues("Mattie")
        end):set_selected_tar_scale(1.05):set_triggered_scale_offset(0.1))
        v_u_22 = p_u_15:add_cycle_element(p_u_14, 1, v_u_4:new(v_u_3:new(p_u_15, p_u_17.PrimaryPart, p_u_17.Marie), p_u_14._spui, function() --[[ Line: 90 ]]
            --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_6, (copy 3): p_u_23 ]]
            p_u_14._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            p_u_23:load_from_pressed_dialogues("Marie")
        end):set_selected_tar_scale(1.05):set_triggered_scale_offset(0.1))
        p_u_23:load_from_startup_dialogues()
    end;
    local v_u_24 = false
    v18.set_locked = function(_, p25) --[[ Name: set_locked ]] --[[ Line: 100 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        v_u_24 = p25
    end;
    v18.song_selected = function(p26, p27) --[[ Name: song_selected ]] --[[ Line: 104 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_1, (ref 4): v_u_11 ]]
        if v_u_24 == true then
            return;
        else
            local v_u_28 = v_u_7:singleton():key_to_name(p27)
            local v30 = v_u_1:splist_filter(v_u_11, function(p29) --[[ Line: 107 ]]
                --[[ Upvalues: (copy 1): v_u_28 ]]
                return v_u_28 == p29.Songname;
            end)
            if v30:count() > 0 then
                p26:load_dialogue(v30:random())
            else
                p26:load_dialogue(nil)
            end;
        end;
    end;
    v18.song_purchased = function(p31, _) --[[ Name: song_purchased ]] --[[ Line: 117 ]]
        --[[ Upvalues: (ref 1): v_u_13 ]]
        p31:load_dialogue(v_u_13:random())
    end;
    v18.load_from_startup_dialogues = function(p32) --[[ Name: load_from_startup_dialogues ]] --[[ Line: 121 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_10, (ref 3): v_u_9 ]]
        local v34 = v_u_1:splist_filter(v_u_10, function(p33) --[[ Line: 122 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            if v_u_9 == false then
                return p33.Firsttime == true;
            else
                return p33.Firsttime ~= true;
            end;
        end)
        v_u_9 = true
        p32:load_dialogue(v34:random())
    end;
    v18.load_from_pressed_dialogues = function(p35, p_u_36) --[[ Name: load_from_pressed_dialogues ]] --[[ Line: 133 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_12 ]]
        p35:load_dialogue(v_u_1:splist_filter(v_u_12, function(p37) --[[ Line: 134 ]]
            --[[ Upvalues: (copy 1): p_u_36 ]]
            return p37[p_u_36] ~= nil;
        end):random())
    end;
    v18.load_dialogue = function(_, p38) --[[ Name: load_dialogue ]] --[[ Line: 140 ]]
        --[[ Upvalues: (ref 1): v_u_19, (copy 2): p_u_14, (ref 3): v_u_20 ]]
        local v39, v_u_40
        if p38 == nil then
            v39 = nil
            v_u_40 = nil
        else
            v39 = p38.Mattie
            v_u_40 = p38.Marie
        end;
        local v41 = 0
        if v39 == nil then
            v_u_19:finish()
        else
            v_u_19:display_text(v39)
            v41 = 50
        end;
        if v_u_40 == nil then
            v_u_20:finish()
        else
            p_u_14._update_enqueue_fn:enqueue_function(function() --[[ Line: 155 ]]
                --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_40 ]]
                v_u_20:display_text(v_u_40)
            end, v41)
        end;
    end;
    local function _(p42) --[[ Name: dialogue_time_finish ]] --[[ Line: 163 ]]
        if p42:is_displayed() and p42:get_time_displayed() > 5 then
            p42:finish()
        end;
    end;
    v18.update = function(_, p43) --[[ Name: update ]] --[[ Line: 169 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_20 ]]
        v_u_19:update(p43)
        v_u_20:update(p43)
        local v44 = v_u_19
        if v44:is_displayed() and v44:get_time_displayed() > 5 then
            v44:finish()
        end;
        local v45 = v_u_20
        if v45:is_displayed() and v45:get_time_displayed() > 5 then
            v45:finish()
        end;
    end;
    v18.layout = function(_) --[[ Name: layout ]] --[[ Line: 177 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_20 ]]
        v_u_19:layout()
        v_u_20:layout()
    end;
    v18.set_alpha = function(_, p46) --[[ Name: set_alpha ]] --[[ Line: 182 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_20 ]]
        v_u_19:set_alpha(p46)
        v_u_20:set_alpha(p46)
    end;
    v18:cons()
    return v18;
end;
return v8;
